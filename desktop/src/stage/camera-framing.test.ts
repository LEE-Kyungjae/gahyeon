import { describe, expect, it } from 'vitest'
import {
  cameraFraming,
  lookingGlassCameraDistance,
  lookingGlassFog,
  lookingGlassFraming,
} from './three-stage'

describe('desktop character camera framing', () => {
  it('moves progressively closer from full body to bust to face', () => {
    const full = cameraFraming('full-body')
    const bust = cameraFraming('bust')
    const face = cameraFraming('face')
    expect(full.offset.z).toBeGreaterThan(bust.offset.z)
    expect(bust.offset.z).toBeGreaterThan(face.offset.z)
    expect(face.target.y).toBeGreaterThan(bust.target.y)
    expect(bust.target.y).toBeGreaterThan(full.target.y)
  })
})

describe('Looking Glass framing', () => {
  it('matches the @lookingglass/webxr camera distance formula', () => {
    // 0.5 * 3.2 / tan(7 deg)
    expect(lookingGlassCameraDistance(3.2)).toBeCloseTo(13.03, 2)
  })

  it('aims at the same height as the monitor preset and tightens with closer presets', () => {
    const presets = ['full-body', 'bust', 'face'] as const
    for (const preset of presets) {
      expect(lookingGlassFraming(preset).targetY).toBe(cameraFraming(preset).target.y)
    }
    expect(lookingGlassFraming('full-body').targetDiam)
      .toBeGreaterThan(lookingGlassFraming('bust').targetDiam)
    expect(lookingGlassFraming('bust').targetDiam)
      .toBeGreaterThan(lookingGlassFraming('face').targetDiam)
  })

  it('keeps the character in front of the fog at the Looking Glass camera distance', () => {
    for (const preset of ['full-body', 'bust', 'face'] as const) {
      const distance = lookingGlassCameraDistance(lookingGlassFraming(preset).targetDiam)
      const framing = cameraFraming(preset)
      const monitorGap = 9 - framing.offset.distanceTo(framing.target)
      expect(lookingGlassFog(preset).near - distance).toBeCloseTo(monitorGap, 6)
      expect(lookingGlassFog(preset).near).toBeGreaterThan(distance)
    }
  })
})
