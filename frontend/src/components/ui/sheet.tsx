"use client"

import * as React from "react"
import { Dialog as SheetPrimitive } from "@base-ui/react/dialog"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { XIcon } from "lucide-react"

/** The floating Ask the Brain and Feedback tools (and anything they open) carry data-feedback-ui. */
function fromFloatingTools(event: Event | undefined) {
  const inside = (n: unknown) => n instanceof Element && !!n.closest("[data-feedback-ui]")
  const related = event && "relatedTarget" in event ? (event as FocusEvent).relatedTarget : null
  return inside(event?.target) || inside(related)
}

/** Side panels don't lock the page (modal={false}), so Ask the Brain and Feedback keep working while one is open,
 * and using them never closes it. Clicking the dimmed page, Escape or the cross still closes it. Pass modal
 * where a panel must lock the page (the phone menu). */
function Sheet({ modal = false, onOpenChange, ...props }: SheetPrimitive.Root.Props) {
  return (
    <SheetPrimitive.Root
      data-slot="sheet"
      modal={modal}
      onOpenChange={(open, details) => {
        if (!open && fromFloatingTools(details.event)) {
          details.cancel()
          return
        }
        onOpenChange?.(open, details)
      }}
      {...props}
    />
  )
}

function SheetTrigger({ ...props }: SheetPrimitive.Trigger.Props) {
  return <SheetPrimitive.Trigger data-slot="sheet-trigger" {...props} />
}

function SheetClose({ ...props }: SheetPrimitive.Close.Props) {
  return <SheetPrimitive.Close data-slot="sheet-close" {...props} />
}

function SheetPortal({ ...props }: SheetPrimitive.Portal.Props) {
  return <SheetPrimitive.Portal data-slot="sheet-portal" {...props} />
}

function SheetOverlay({ className, ...props }: SheetPrimitive.Backdrop.Props) {
  return (
    <SheetPrimitive.Backdrop
      data-slot="sheet-overlay"
      className={cn(
        "fixed inset-0 z-50 bg-black/10 transition-opacity duration-150 data-ending-style:opacity-0 data-starting-style:opacity-0 supports-backdrop-filter:backdrop-blur-xs",
        className
      )}
      {...props}
    />
  )
}

/** CSS variable the floating Ask the Brain and Feedback buttons use for their distance from the right edge. */
const FLOATING_RIGHT = "--floating-tools-right"

// One width for every side panel, remembered in this browser: widen one and the others open wide too.
const WIDTH_KEY = "bmi.sheet-width"
const MIN_WIDTH = 360
const STEP = 48
const widest = () => Math.max(MIN_WIDTH, window.innerWidth - 64)
const clampWidth = (w: number) => Math.round(Math.min(widest(), Math.max(MIN_WIDTH, w)))

function readWidth(): number | null {
  try {
    const v = Number(window.localStorage.getItem(WIDTH_KEY))
    return v >= MIN_WIDTH ? v : null
  } catch {
    return null
  }
}

function saveWidth(w: number | null) {
  try {
    if (w) window.localStorage.setItem(WIDTH_KEY, String(w))
    else window.localStorage.removeItem(WIDTH_KEY)
  } catch {
    // private window or blocked storage: the width just isn't remembered
  }
}

/** The grip on a side panel's inner edge: drag it (or focus it and use the arrow keys) to make the panel wider or
 * narrower; double-click it to go back to the panel's usual width. */
function ResizeHandle({
  side,
  panel,
  width,
  onWidth,
}: {
  side: "left" | "right"
  panel: React.RefObject<HTMLDivElement | null>
  width: number | null
  onWidth: (w: number | null, save?: boolean) => void
}) {
  const drag = React.useRef<{ x: number; w: number } | null>(null)
  const [dragging, setDragging] = React.useState(false)
  const current = () => width ?? panel.current?.getBoundingClientRect().width ?? MIN_WIDTH
  // the edge being dragged is the inner one, so moving towards the page's middle widens the panel
  const widthAt = (x: number) => clampWidth(drag.current!.w + (side === "right" ? drag.current!.x - x : x - drag.current!.x))

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      aria-valuemin={MIN_WIDTH}
      aria-valuenow={Math.round(current())}
      tabIndex={0}
      title="Drag to resize. Double-click to go back to the usual width."
      data-side={side}
      data-dragging={dragging ? "" : undefined}
      className="group/resize absolute inset-y-0 z-10 hidden w-3 cursor-col-resize touch-none outline-none select-none data-[side=left]:-right-1.5 data-[side=right]:-left-1.5 sm:block"
      onPointerDown={(e) => {
        if (e.button !== 0) return
        e.preventDefault()
        e.currentTarget.setPointerCapture(e.pointerId)
        drag.current = { x: e.clientX, w: current() }
        setDragging(true)
        document.body.style.cursor = "col-resize"
      }}
      onPointerMove={(e) => {
        if (drag.current) onWidth(widthAt(e.clientX))
      }}
      onPointerUp={(e) => {
        if (!drag.current) return
        onWidth(widthAt(e.clientX), true)
        drag.current = null
        setDragging(false)
        document.body.style.cursor = ""
      }}
      onPointerCancel={() => {
        drag.current = null
        setDragging(false)
        document.body.style.cursor = ""
      }}
      onDoubleClick={() => onWidth(null, true)}
      onKeyDown={(e) => {
        const grow = side === "right" ? "ArrowLeft" : "ArrowRight"
        const shrink = side === "right" ? "ArrowRight" : "ArrowLeft"
        if (e.key !== grow && e.key !== shrink && e.key !== "Home" && e.key !== "End") return
        e.preventDefault()
        if (e.key === "Home") onWidth(null, true)
        else if (e.key === "End") onWidth(clampWidth(widest()), true)
        else onWidth(clampWidth(current() + (e.key === grow ? STEP : -STEP)), true)
      }}
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-transparent transition-colors group-hover/resize:bg-ring/60 group-focus-visible/resize:bg-ring group-data-dragging/resize:bg-ring"
      />
      <span
        aria-hidden="true"
        className="absolute top-1/2 left-1/2 h-10 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-border bg-background shadow-sm transition-colors group-hover/resize:border-ring group-hover/resize:bg-ring group-focus-visible/resize:border-ring group-focus-visible/resize:bg-ring group-data-dragging/resize:border-ring group-data-dragging/resize:bg-ring"
      />
    </div>
  )
}

function SheetContent({
  className,
  children,
  side = "right",
  showCloseButton = true,
  resizable = true,
  style,
  ...props
}: SheetPrimitive.Popup.Props & {
  side?: "top" | "right" | "bottom" | "left"
  showCloseButton?: boolean
  /** Left and right panels get a drag handle on their inner edge (from tablet width up). */
  resizable?: boolean
}) {
  const canResize = resizable && (side === "left" || side === "right")
  const panel = React.useRef<HTMLDivElement | null>(null)
  const watcher = React.useRef<ResizeObserver | null>(null)
  // A right-hand panel tells the floating Ask the Brain and Feedback buttons how wide it is, so they sit just
  // outside its edge instead of on top of its Save button (see FLOATING_RIGHT). Not when it fills the screen.
  const setPanel = React.useCallback(
    (node: HTMLDivElement | null) => {
      panel.current = node
      watcher.current?.disconnect()
      const root = document.documentElement
      if (!node || side !== "right") {
        root.style.removeProperty(FLOATING_RIGHT)
        return
      }
      watcher.current = new ResizeObserver(() => {
        const w = node.getBoundingClientRect().width
        if (window.innerWidth - w >= 220) root.style.setProperty(FLOATING_RIGHT, `${Math.round(w) + 16}px`)
        else root.style.removeProperty(FLOATING_RIGHT)
      })
      watcher.current.observe(node)
    },
    [side]
  )
  const [width, setWidth] = React.useState<number | null>(() =>
    canResize && typeof window !== "undefined" ? readWidth() : null
  )
  const onWidth = React.useCallback((w: number | null, save = false) => {
    setWidth(w)
    if (save) saveWidth(w)
  }, [])

  return (
    <SheetPortal>
      <SheetOverlay />
      <SheetPrimitive.Popup
        ref={setPanel}
        data-slot="sheet-content"
        data-side={side}
        data-resized={canResize && width ? "" : undefined}
        style={canResize && width ? ({ ...(style as React.CSSProperties), "--sheet-w": `${width}px` } as React.CSSProperties) : style}
        className={cn(
          "fixed z-50 flex flex-col gap-4 bg-popover bg-clip-padding text-sm text-popover-foreground shadow-lg transition duration-200 ease-in-out data-ending-style:opacity-0 data-starting-style:opacity-0 data-[side=bottom]:inset-x-0 data-[side=bottom]:bottom-0 data-[side=bottom]:h-auto data-[side=bottom]:border-t data-[side=bottom]:data-ending-style:translate-y-[2.5rem] data-[side=bottom]:data-starting-style:translate-y-[2.5rem] data-[side=left]:inset-y-0 data-[side=left]:left-0 data-[side=left]:h-full data-[side=left]:border-r data-[side=left]:data-ending-style:translate-x-[-2.5rem] data-[side=left]:data-starting-style:translate-x-[-2.5rem] data-[side=right]:inset-y-0 data-[side=right]:right-0 data-[side=right]:h-full data-[side=right]:border-l data-[side=right]:data-ending-style:translate-x-[2.5rem] data-[side=right]:data-starting-style:translate-x-[2.5rem] data-[side=top]:inset-x-0 data-[side=top]:top-0 data-[side=top]:h-auto data-[side=top]:border-b data-[side=top]:data-ending-style:translate-y-[-2.5rem] data-[side=top]:data-starting-style:translate-y-[-2.5rem] @container/sheet",
          // the usual size of a side panel, as plain classes so a panel's own width (e.g. sm:max-w-xl) replaces it -
          // as attribute rules they used to win, which held every side panel to 384px
          (side === "left" || side === "right") && "w-3/4 sm:max-w-sm",
          className,
          // a width the person chose wins over the panel's usual one (the attribute makes it the more specific rule)
          canResize && "sm:data-resized:w-(--sheet-w)! sm:data-resized:max-w-[calc(100vw-4rem)]!"
        )}
        {...props}
      >
        {canResize && <ResizeHandle side={side as "left" | "right"} panel={panel} width={width} onWidth={onWidth} />}
        {children}
        {showCloseButton && (
          <SheetPrimitive.Close
            data-slot="sheet-close"
            render={
              <Button
                variant="ghost"
                className="absolute top-3 right-3"
                size="icon-sm"
              />
            }
          >
            <XIcon
            />
            <span className="sr-only">Close</span>
          </SheetPrimitive.Close>
        )}
      </SheetPrimitive.Popup>
    </SheetPortal>
  )
}

function SheetHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-header"
      className={cn("flex flex-col gap-0.5 p-4", className)}
      {...props}
    />
  )
}

function SheetFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-footer"
      className={cn("mt-auto flex flex-col gap-2 p-4", className)}
      {...props}
    />
  )
}

function SheetTitle({ className, ...props }: SheetPrimitive.Title.Props) {
  return (
    <SheetPrimitive.Title
      data-slot="sheet-title"
      className={cn(
        "font-heading text-base font-medium text-foreground",
        className
      )}
      {...props}
    />
  )
}

function SheetDescription({
  className,
  ...props
}: SheetPrimitive.Description.Props) {
  return (
    <SheetPrimitive.Description
      data-slot="sheet-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}
