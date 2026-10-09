import { createInterface } from 'node:readline'
import { Asterion256 } from '../dist/Asterion-256.js'

// Read one JSON array of test cases. The caller independently computes Python hashes.
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
for await (const line of lines) {
  const rows = JSON.parse(line)
  const output = rows.map((item) => {
    const h = new Asterion256(item.domain)
    if (Array.isArray(item.stringChunks)) {
      for (const chunk of item.stringChunks) h.update(chunk)
    } else if (Array.isArray(item.byteChunks)) {
      for (const chunk of item.byteChunks) h.update(Buffer.from(chunk, 'hex'))
    } else {
      h.update(Buffer.from(item.messageHex, 'hex'))
    }
    return h.digest('hex')
  })
  process.stdout.write(JSON.stringify(output) + '\n')
}
