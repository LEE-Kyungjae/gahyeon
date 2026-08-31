#!/usr/bin/env node

const { spawn } = require('node:child_process')
const path = require('node:path')
const HoloPlayCore = require('../native/macos/GahyeonLookingGlassBridge/node_modules/holoplay-core')

const root = path.resolve(__dirname, '..')
const encoder = path.join(root, '.build/macos-looking-glass/GahyeonLookingGlassFrameEncoder')
let client
let pending = Buffer.alloc(0)
let latestFrame = null
let sending = false

function fail(message, error) {
  console.error(`GAHYEON_LKG_STREAM_ERROR ${message}`, error || '')
  process.exitCode = 2
  shutdown()
}

function sendLatest() {
  if (sending || !latestFrame || !client) return
  const frame = latestFrame
  latestFrame = null
  sending = true
  client.sendMessage(new HoloPlayCore.ShowMessage(
    { vx: 11, vy: 6, aspect: 0.5625 }, frame, 0,
  ), 5).then(() => {
    if (!sendLatest.announced) {
      console.log('GAHYEON_LKG_LIVE_STREAM_READY')
      sendLatest.announced = true
    }
  }).catch(error => fail('Bridge rejected Unreal frame', error)).finally(() => {
    sending = false
    sendLatest()
  })
}

const child = spawn(encoder, [], { stdio: ['ignore', 'pipe', 'inherit'] })
child.stdout.on('data', chunk => {
  pending = Buffer.concat([pending, chunk])
  while (pending.length >= 4) {
    const length = pending.readUInt32BE(0)
    if (pending.length < 4 + length) break
    latestFrame = pending.subarray(4, 4 + length)
    pending = pending.subarray(4 + length)
  }
  sendLatest()
})
child.on('error', error => fail('frame encoder failed', error))
child.on('exit', code => { if (code && !process.exitCode) fail(`frame encoder exited ${code}`) })

client = new HoloPlayCore.Client(
  info => {
    if (!info.devices || info.devices.length === 0) return fail('no Looking Glass device')
    sendLatest()
  },
  error => fail('Bridge connection failed', error),
  () => { if (!process.exitCode) fail('Bridge connection closed') },
  false,
  'gahyeon-unreal-live-v001',
  true,
  'wipe',
)

let stopping = false
function shutdown() {
  if (stopping) return
  stopping = true
  child.kill('SIGTERM')
  if (client) client.disconnect()
  setTimeout(() => process.exit(process.exitCode || 0), 100).unref()
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
