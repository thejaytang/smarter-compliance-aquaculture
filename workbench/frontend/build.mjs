import {build} from 'esbuild';
import {mkdir,copyFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
await mkdir(root+'../ui/vendor/markdown',{recursive:true});
await build({stdin:{contents:"export {default as MarkdownIt} from 'markdown-it'; export {diffWordsWithSpace,diffChars} from 'diff';",resolveDir:root,sourcefile:'markdown-tools.js'},bundle:true,format:'esm',platform:'browser',target:'es2022',minify:true,legalComments:'eof',outfile:root+'../ui/vendor/markdown/tools.mjs'});
for(const [name,file] of [['markdown-it','LICENSE'],['diff','LICENSE'],['entities','LICENSE'],['linkify-it','LICENSE'],['mdurl','LICENSE'],['punycode.js','LICENSE-MIT.txt'],['uc.micro','LICENSE.txt'],['argparse','LICENSE']])await copyFile(root+'node_modules/'+name+'/'+file,root+'../ui/vendor/markdown/'+name+'-LICENSE');
