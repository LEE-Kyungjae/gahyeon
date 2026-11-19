declare module '@lookingglass/webxr' {
  export interface LookingGlassViewConfig {
    tileHeight: number
    numViews: number
    targetX: number
    targetY: number
    targetZ: number
    targetDiam: number
    trackballX: number
    trackballY: number
    fovy: number
    depthiness: number
    inlineView: number
  }

  export class LookingGlassWebXRPolyfill {
    constructor(config?: Partial<LookingGlassViewConfig>)
    isPresenting: boolean
  }

  /** The library's global configuration instance (0.6.x exports the instance, not the class). */
  export const LookingGlassConfig: {
    updateViewControls(config: Partial<LookingGlassViewConfig>): void
  }
}
