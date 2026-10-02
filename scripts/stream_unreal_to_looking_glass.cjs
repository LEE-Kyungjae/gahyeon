#!/usr/bin/env node

const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const root = path.resolve(__dirname, '..')
const encoder = path.join(root, '.build/macos-looking-glass/GahyeonLookingGlassFrameEncoder')
const quiltDirectory = path.join(root, '.build/macos-looking-glass/live-quilts')
const bridgeBase = 'http://localhost:33334/'
let child
let orchestration
let currentPlaylist
let playlistSequence = 0
let pending = Buffer.alloc(0)
let latestFrame = null
let sending = false
let stopping = false

async function bridgePut(endpoint, requestBody, timeoutMs = 15000) {
  const response = await fetch(bridgeBase + endpoint, {
    method: 'PUT', headers: { 'content-type': 'application/json' },
    body: JSON.stringify(requestBody), signal: AbortSignal.timeout(timeoutMs),
  })
  if (!response.ok) throw new Error(`${endpoint} returned HTTP ${response.status}`)
  const value = await response.json()
  const status = value?.status?.value
  if (status !== 'Completion' && status !== 'Pending') {
    throw new Error(`${endpoint} returned Bridge status ${status || 'missing'}`)
  }
  return value
}

async function connectBridge() {
  const entered = await bridgePut('enter_orchestration', { name: 'gahyeon-unreal-live' })
  orchestration = entered?.payload?.value
  if (!orchestration) throw new Error('Bridge did not return an orchestration token')
  const outputs = await bridgePut('available_output_devices', { orchestration })
  const devices = Object.values(outputs?.payload?.value || {}).map(item => item.value)
  const lookingGlass = devices.find(device =>
    device?.hwid?.value?.startsWith('LKG-') && device?.state?.value === 'ok')
  if (!lookingGlass) throw new Error('no ready LKG output in Bridge 2 device list')
  console.log(`GAHYEON_LKG_DEVICE_READY ${lookingGlass.hwid.value} index=${lookingGlass.index.value}`)
}

async function castLatest() {
  if (sending || !latestFrame || !orchestration) return
  const frame = latestFrame
  latestFrame = null
  sending = true
  const sequence = playlistSequence++
  const quiltPath = path.join(quiltDirectory, `gahyeon-live-${sequence % 2}_qs11x6a0.5625.jpg`)
  const playlist = `GahyeonLive${sequence}`
  try {
    fs.writeFileSync(quiltPath, frame)
    await bridgePut('instance_playlist', { orchestration, name: playlist, loop: true })
    await bridgePut('insert_playlist_entry', {
      orchestration, id: 0, name: playlist, index: 0, uri: quiltPath,
      rows: 6, cols: 11, focus: 0, aspect: 0.5625, view_count: 66,
      isRGBD: 0, tag: 'gahyeon-unreal-live',
    })
    await bridgePut('play_playlist', { orchestration, name: playlist, head_index: -1 })
    await bridgePut('show_window', { orchestration, show_window: true, head_index: -1 })
    if (currentPlaylist) {
      bridgePut('delete_playlist', { orchestration, name: currentPlaylist, loop: true }).catch(() => {})
    }
    currentPlaylist = playlist
    if (!castLatest.announced) {
      console.log('GAHYEON_LKG_PHYSICAL_PLAYLIST_READY')
      castLatest.announced = true
    }
  } catch (error) {
    fail('Bridge 2 rejected Unreal quilt', error)
  } finally {
    sending = false
    castLatest()
  }
}

function fail(message, error) {
  console.error(`GAHYEON_LKG_STREAM_ERROR ${message}`, error || '')
  process.exitCode = 2
  shutdown()
}

function shutdown() {
  if (stopping) return
  stopping = true
  if (child) child.kill('SIGTERM')
  setTimeout(() => process.exit(process.exitCode || 0), 100).unref()
}

async function main() {
  fs.mkdirSync(quiltDirectory, { recursive: true })
  await connectBridge()
  child = spawn(encoder, [], { stdio: ['ignore', 'pipe', 'inherit'] })
  child.stdout.on('data', chunk => {
    pending = Buffer.concat([pending, chunk])
    while (pending.length >= 4) {
      const length = pending.readUInt32BE(0)
      if (pending.length < 4 + length) break
      latestFrame = pending.subarray(4, 4 + length)
      pending = pending.subarray(4 + length)
    }
    castLatest()
  })
  child.on('error', error => fail('frame encoder failed', error))
  child.on('exit', code => { if (!stopping) fail(`frame encoder exited ${code}`, '') })
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
main().catch(error => fail('Bridge 2 connection failed', error))
