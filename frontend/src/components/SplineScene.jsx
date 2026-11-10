import { lazy, Suspense } from 'react'
import { Box, MousePointer2 } from 'lucide-react'

const Spline = lazy(() => import('@splinetool/react-spline'))

export function SplineScene() {
  const sceneUrl = import.meta.env.VITE_SPLINE_SCENE_URL

  return (
    <div className="relative h-[330px] overflow-hidden rounded-[2rem] border border-white/15 bg-slate-950 sm:h-[430px]">
      {sceneUrl ? (
        <Suspense fallback={<SceneFallback />}>
          <Spline scene={sceneUrl} />
        </Suspense>
      ) : (
        <SceneFallback />
      )}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-slate-950/90 to-transparent px-6 pb-5 pt-14 text-white">
        <div>
          <p className="text-sm font-semibold">Your city, in motion</p>
          <p className="mt-1 text-xs text-slate-300">A live view of every delivery journey</p>
        </div>
        <span className="grid size-10 place-items-center rounded-full border border-white/20 bg-white/10">
          <MousePointer2 size={17} />
        </span>
      </div>
    </div>
  )
}

function SceneFallback() {
  return (
    <div className="scene-fallback relative grid h-full place-items-center overflow-hidden">
      <div className="scene-grid absolute inset-0" />
      <div className="scene-orbit orbit-one" />
      <div className="scene-orbit orbit-two" />
      <div className="scene-globe">
        <div className="scene-globe-shine" />
        <div className="scene-globe-route route-one" />
        <div className="scene-globe-route route-two" />
        <span className="scene-globe-pin pin-one"><Box size={15} /></span>
        <span className="scene-globe-pin pin-two"><Box size={15} /></span>
        <span className="scene-globe-pin pin-three"><Box size={15} /></span>
      </div>
      <div className="absolute left-[12%] top-[20%] rounded-2xl border border-white/10 bg-white/10 p-3 text-white shadow-xl backdrop-blur-md">
        <p className="text-[10px] uppercase tracking-[0.18em] text-blue-200">In transit</p>
        <p className="mt-1 text-sm font-bold">Across the city</p>
      </div>
      <div className="absolute bottom-[24%] right-[8%] rounded-2xl border border-white/10 bg-white/10 p-3 text-white shadow-xl backdrop-blur-md">
        <p className="text-[10px] uppercase tracking-[0.18em] text-emerald-200">Delivered</p>
        <p className="mt-1 text-sm font-bold">Right on time</p>
      </div>
    </div>
  )
}
