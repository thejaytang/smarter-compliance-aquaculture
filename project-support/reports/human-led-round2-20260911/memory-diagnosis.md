# Bounded large-response memory diagnosis

## Scope and method

This isolated experiment made 100 sequential HTTP reads per fresh child server, using a synthetic 600,000-cell material with a 7,306,795-byte JSON response. It used the product's existing `Handler.send`, but did not instantiate `Application`, access business databases, or restart the normal workbench or acceptance server. A four-worker executor was an experimental control only; it was not added to the product.

Each child reported current resident memory through macOS `proc_pidinfo`, Python live and peak traced allocations through `tracemalloc`, and garbage-collector object counts. Current RSS is not the process lifetime high-water mark. The payload for fixed-object controls was constructed before tracing, so traced bytes describe subsequent allocations, not the retained baseline fixture object.

## Results

All figures below use decimal MB. Each row is a separate child process.

| Control | Initial RSS | Maximum sampled RSS | RSS after 100 reads | Live traced allocations after 100 | Mean request time |
| --- | ---: | ---: | ---: | ---: | ---: |
| New thread per request, decode then encode each time | 47.25 | 157.89 | 157.89 | 0.176 | 0.412 s |
| Reused workers, decode then encode each time | 47.33 | 158.11 | 153.12 | 0.190 | 0.431 s |
| New thread per request, encode the same fixed object | 88.93 | 528.79 | 446.58 | 0.242 | 0.320 s |
| Reused workers, encode the same fixed object | 88.82 | 550.40 | 550.40 | 0.183 | 0.281 s |
| New thread per request, send existing encoded bytes | 88.97 | 89.24 | 89.24 | 0.242 | 0.001 s |

The fixed-object, new-thread control rose approximately 7.3 MB per read through the first 60 reads, then fell and rose again. The equivalent reused-worker control followed the same initial increase and plateaued near 550 MB from 70 to 100 reads. A final explicit garbage collection did not reduce that reused-worker RSS. After collection, incremental tracked object counts were 188–288 in the decode controls and 193–238 in the fixed-object controls. No response-sized Python object accumulation appeared in these samples.

## Interpretation and limits

Dynamic JSON serialization and UTF-8 response allocation are sufficient to reproduce the observed RSS increase without the source adapter, workflow store, or background workers. Sending the same encoded bytes through the existing HTTP implementation stays flat. Reusing request threads does not remove the effect. The results support allocation-pattern and native allocator resident-memory retention as the proximate explanation; they do not support adding a production worker pool or forced garbage collection as a fix.

Live traced Python allocations and RSS measure different things. Low live traced allocations do not prove that every possible native leak is absent, and sampled RSS plateaus or reclamation do not establish stability for every payload or operating-system condition. This is a bounded 100-read experiment per control, not a multi-day reliability guarantee. It explains the observed pattern and narrows the next investigation if real usage exceeds these bounds; it does not certify all future memory behavior.

## Reproduction and evidence

Run from the workstream root:

```sh
PYTHONPATH=workbench/src workbench/.venv/bin/python workbench/scripts/diagnose_http_reader_memory.py workbench/runtime/round2-acceptance/http-allocation-diagnosis.json
PYTHONPATH=workbench/src workbench/.venv/bin/python workbench/scripts/diagnose_http_reader_memory.py workbench/runtime/round2-acceptance/http-pool-fixed-diagnosis.json pool-fixed
```

The two JSON files contain every sampled RSS/live-allocation/object count and all 100 request timings for each control. The experiment-only script is `workbench/scripts/diagnose_http_reader_memory.py`. It creates fresh ephemeral loopback servers and terminates only its own child processes.
