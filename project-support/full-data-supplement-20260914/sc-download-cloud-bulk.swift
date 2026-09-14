import Foundation
import Darwin
let mode = CommandLine.arguments[1]
let input = CommandLine.arguments[2]
let paths = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: input))) as! [String]
var results: [[String: Any]] = []
for (index,path) in paths.enumerated() {
    let url = URL(fileURLWithPath: path)
    var row: [String:Any] = ["path":path]
    do {
        let values = try url.resourceValues(forKeys: [.isUbiquitousItemKey, .ubiquitousItemDownloadingStatusKey, .ubiquitousItemIsDownloadingKey, .ubiquitousItemIsUploadedKey, .ubiquitousItemDownloadingErrorKey])
        row["ubiquitous"] = values.isUbiquitousItem ?? false
        row["status"] = values.ubiquitousItemDownloadingStatus?.rawValue ?? "unknown"
        row["uploaded"] = values.ubiquitousItemIsUploaded ?? false
        row["downloading"] = values.ubiquitousItemIsDownloading ?? false
        if let error = values.ubiquitousItemDownloadingError {row["downloadError"] = error.localizedDescription}
        if mode == "download" || mode == "download-and-wait" {
            try FileManager.default.startDownloadingUbiquitousItem(at:url)
            row["request"] = "accepted"
        }
    } catch {row["error"] = String(describing:error)}
    results.append(row)
    if paths.count <= 3 || (index+1)%50 == 0 {print("Processed \(index+1)/\(paths.count)")}
}
let data = try JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted,.sortedKeys])
try data.write(to: URL(fileURLWithPath:CommandLine.arguments[3]))
print("Finished \(paths.count) requests")

if mode == "download-and-wait" {
    let end = Date().addingTimeInterval(1800)
    var remaining = paths
    while !remaining.isEmpty && Date() < end {
        RunLoop.current.run(until:Date().addingTimeInterval(30))
        remaining = remaining.filter { path in
            var info = stat()
            return lstat(path, &info) != 0 || (info.st_flags & 0x40000000) != 0
        }
        print("LOCAL_CONTENT_PENDING \(remaining.count)/\(paths.count)")
        fflush(stdout)
    }
}
