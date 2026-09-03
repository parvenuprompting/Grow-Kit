// Genereer het AppIcon (kiemplant, editorial monochrome) als 1024px PNG.
// Ontwerp v2: macOS-squircle, hairline-kader, gebogen steel met twee bladeren
// (één vol, één 55% — de mockup-tweeheid), bladnerven en een grondlijn met
// opening. Gebruik: swift Scripts/genereer-icon.swift
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

// achtergrond: macOS-squircle
ctx.setFillColor(NSColor.black.cgColor)
ctx.addPath(CGPath(roundedRect: CGRect(x: 0, y: 0, width: 64, height: 64),
                   cornerWidth: 14.5, cornerHeight: 14.5, transform: nil))
ctx.fillPath()

// hairline-binnenkader (de "Kaart"-lijn uit de huisstijl, geïnverteerd)
ctx.setStrokeColor(NSColor.white.withAlphaComponent(0.14).cgColor)
ctx.setLineWidth(0.22)
ctx.addPath(CGPath(roundedRect: CGRect(x: 2.2, y: 2.2, width: 59.6, height: 59.6),
                   cornerWidth: 12.3, cornerHeight: 12.3, transform: nil))
ctx.strokePath()

// grondlijn met opening waar de steel staat
ctx.setStrokeColor(NSColor.white.withAlphaComponent(0.20).cgColor)
ctx.setLineWidth(0.28)
ctx.setLineCap(.round)
ctx.move(to: CGPoint(x: 15, y: 52)); ctx.addLine(to: CGPoint(x: 27, y: 52))
ctx.move(to: CGPoint(x: 37, y: 52)); ctx.addLine(to: CGPoint(x: 49, y: 52))
ctx.strokePath()

// steel: gebogen S-lijn van de grond naar het bladpaar
ctx.setStrokeColor(NSColor.white.cgColor)
ctx.setLineWidth(1.1)
ctx.move(to: CGPoint(x: 32, y: 52))
ctx.addCurve(to: CGPoint(x: 32, y: 31),
             control1: CGPoint(x: 29.5, y: 45), control2: CGPoint(x: 34.5, y: 39))
ctx.strokePath()

// linker blad: vol wit, met nerf in de achtergrondkleur
ctx.setFillColor(NSColor.white.cgColor)
let linkerBlad = CGMutablePath()
linkerBlad.move(to: CGPoint(x: 31.6, y: 33))
linkerBlad.addCurve(to: CGPoint(x: 8.5, y: 14.5),
                    control1: CGPoint(x: 31.6, y: 20), control2: CGPoint(x: 21, y: 14.5))
linkerBlad.addCurve(to: CGPoint(x: 31.6, y: 33),
                    control1: CGPoint(x: 9.5, y: 28.5), control2: CGPoint(x: 19, y: 33))
linkerBlad.closeSubpath()
ctx.addPath(linkerBlad)
ctx.fillPath()
ctx.setStrokeColor(NSColor.black.cgColor)
ctx.setLineWidth(0.42)
ctx.move(to: CGPoint(x: 30, y: 31.5))
ctx.addQuadCurve(to: CGPoint(x: 11, y: 16), control: CGPoint(x: 21.5, y: 26.5))
ctx.strokePath()

// rechter blad: 55% wit — de tweeheid uit de mockups
ctx.setFillColor(NSColor.white.withAlphaComponent(0.55).cgColor)
let rechterBlad = CGMutablePath()
rechterBlad.move(to: CGPoint(x: 32.4, y: 32.6))
rechterBlad.addCurve(to: CGPoint(x: 54.5, y: 19),
                     control1: CGPoint(x: 32.4, y: 21.5), control2: CGPoint(x: 44, y: 18))
rechterBlad.addCurve(to: CGPoint(x: 32.4, y: 32.6),
                     control1: CGPoint(x: 45, y: 31), control2: CGPoint(x: 37.5, y: 32.6))
rechterBlad.closeSubpath()
ctx.addPath(rechterBlad)
ctx.fillPath()

// zaadje: klein gedempt punt bij de voet van de steel
ctx.setFillColor(NSColor.white.withAlphaComponent(0.32).cgColor)
ctx.fillEllipse(in: CGRect(x: 38.6, y: 54.4, width: 2.1, height: 2.1))

NSGraphicsContext.restoreGraphicsState()

let doel = URL(fileURLWithPath: "Assets.xcassets/AppIcon.appiconset/icon-1024.png")
let png = rep.representation(using: .png, properties: [:])!
try! png.write(to: doel)
print("icoon v2 geschreven: \(doel.path)")
