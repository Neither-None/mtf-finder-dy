const PROC = process;
const FS = require('fs');
console.log = (...a) => PROC.stderr.write(a.join(' ') + '\n');
PROC.stderr.write('step1 load signer\n');
require(__dirname + '/node_signer.js');
PROC.stderr.write('step2 read input\n');
const raw = FS.readFileSync(PROC.argv[2] || '/tmp/in.json', 'utf-8');
const input = JSON.parse(raw);
globalThis.document.cookie = input.cookie || '';
PROC.stderr.write('step3 init\n');
try {
  globalThis.window.bdms.init({ aid: 6383, pageId: 6241,
    paths: ['^/webcast/','^/aweme/v1/','^/aweme/v2/','/douplus/','^/api/ad/v1/inspire','/v1/message/send','^/live/','^/captcha/','^/ecom/','^/luna/pc'],
    boe: false, ddrt: 8.5, ic: 8.5 });
} catch (e) { PROC.stderr.write('init err ' + e.message + '\n'); }
PROC.stderr.write('step4 xhr\n');
const xhr = new globalThis.XMLHttpRequest();
xhr.open('GET', input.url);
xhr.send(null);
PROC.stderr.write('step5 done\n');
PROC.stdout.write((xhr._url || input.url), () => { PROC.exit(0); });
setTimeout(() => PROC.exit(0), 3000);
