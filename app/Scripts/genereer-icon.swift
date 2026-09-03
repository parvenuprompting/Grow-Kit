// Genereer het AppIcon (kiemplant, editorial monochrome) als 1024px PNG.
// Gebruik: swift Scripts/genereer-icon.swift
import AppKit

let grootte = 1024
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: grootte, pixelsHigh: grootte,
                           bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                           colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
rep.size = NSSize(width: grootte, height: grootte)
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let ctx = NSGraphicsContext.current!.cgContext
ctx.translateBy(x: 0, y: CGFloat(grootte))
ctx.scaleBy(x: 16, y: -16)   // SVG-ruimte (64-grid, y omlaag)

ctx.setFillColor(NSColor.black.cgColor)
ctx.addPath(CGPath(roundedRect: CGRect(x: 0, y: 0, width: 64, height: 64),
                   cornerWidth: 14, cornerHeight: 14, transform: nil))
ctx.fillPath()

ctx.setStrokeColor(NSColor.white.cgColor)
ctx.setLineWidth(4)
ctx.setLineCap(.round)
ctx.move(to: CGPoint(x: 32, y: 50))
ctx.addCurve(to: CGPoint(x: 32, y: 30),
             control1: CGPoint(x: 32, y: 42), control2: CGPoint(x: 32, y: 38))
ctx.strokePath()

ctx.setFillColor(NSColor.white.cgColor)
let linkerBlad = CGMutablePath()
linkerBlad.move(to: CGPoint(x: 32, y: 32))
linkerBlad.addCurve(to: CGPoint(x: 12, y: 16),
                    control1: CGPoint(x: 32, y: 20), control2: CGPoint(x: 23, y: 16))
linkerBlad.addCurve(to: CGPoint(x: 32, y: 32),
                    control1: CGPoint(x: 12, y: 28), control2: CGPoint(x: 21, y: 32))
linkerBlad.closeSubpath()
ctx.addPath(linkerBlad)
ctx.fillPath()

ctx.setFillColor(NSColor.white.withAlphaComponent(0.55).cgColor)
let rechterBlad = CGMutablePath()
rechterBlad.move(to: CGPoint(x: 32, y: 32))
rechterBlad.addCurve(to: CGPoint(x: 49, y: 18),
                     control1: CGPoint(x: 32, y: 22), control2: CGPoint(x: 39, y: 18))
rechterBlad.addCurve(to: CGPoint(x: 32, y: 32),
                     control1: CGPoint(x: 49, y: 28), control2: CGPoint(x: 39, y: 32))
rechterBlad.closeSubpath()
ctx.addPath(rechterBlad)
ctx.fillPath()

NSGraphicsContext.restoreGraphicsState()

let doel = URL(fileURLWithPath: "Assets.xcassets/AppIcon.appiconset/icon-1024.png")
let png = rep.representation(using: .png, properties: [:])!
try! png.write(to: doel)
print("icoon geschreven: \(doel.path)")
