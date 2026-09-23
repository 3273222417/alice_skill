import { execFileSync } from 'node:child_process';
import { stdin as input, stdout as output } from 'node:process';
import readline from 'node:readline/promises';

import {
  DEFAULT_TIKHUB_BASE_URL,
  installTikHubToken,
} from './tikhub-token.mjs';

export async function readToken({
  inputStream = input,
  outputStream = output,
  stty = execFileSync,
} = {}) {
  if (!inputStream.isTTY) {
    const chunks = [];
    for await (const chunk of inputStream) chunks.push(chunk);
    return Buffer.concat(chunks).toString('utf8').trim();
  }

  const rl = readline.createInterface({ input: inputStream, output: outputStream });
  let echoDisabled = false;
  try {
    stty('stty', ['-echo'], { stdio: ['inherit', 'ignore', 'ignore'] });
    echoDisabled = true;
    const token = await rl.question('请粘贴 TikHub API Token，回车保存到本机钥匙串：');
    return token.trim();
  } finally {
    if (echoDisabled) {
      try {
        stty('stty', ['echo'], { stdio: ['inherit', 'ignore', 'ignore'] });
      } catch {
        // If echo restore fails, leave process cleanup to the terminal session.
      }
      outputStream.write('\n');
    }
    rl.close();
  }
}

export async function main() {
  const token = await readToken();
  if (!token) {
    console.error('未读取到 Token，已退出。');
    process.exit(1);
  }

  const target = installTikHubToken(token);
  console.log('TikHub Token 已保存到本机钥匙串。');
  console.log(`service: ${target.service}`);
  console.log(`account: ${target.account}`);
  console.log(`default_base_url: ${process.env.TIKHUB_BASE_URL || DEFAULT_TIKHUB_BASE_URL}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
