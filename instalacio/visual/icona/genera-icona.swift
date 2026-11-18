// Genera la icona de l'instal·lador visual: un pentagrama amb dues corxeres.
// Ús (en un Mac): swift genera-icona.swift   (escriu Arranjaments.icns, Arranjaments.ico i icona.png al costat)
// Els fitxers generats es guarden al repositori; només cal tornar-lo a executar si es canvia el dibuix.
import AppKit

let ací = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()

func color(_ hex: UInt32) -> CGColor {
    CGColor(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255, blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
}

/// Dibuixa la icona en un quadrat de `mida` píxels. `marge` és la part buida al voltant (proporció del costat).
func dibuixa(mida: Int, marge: CGFloat) -> NSBitmapImageRep {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: mida, pixelsHigh: mida, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                               bytesPerRow: 0, bitsPerPixel: 0)!
    let g = NSGraphicsContext(bitmapImageRep: rep)!.cgContext
    let s = CGFloat(mida)
    let m = s * marge
    let q = CGRect(x: m, y: m, width: s - 2 * m, height: s - 2 * m)
    let u = q.width / 100  // unitat: el quadrat útil fa 100 x 100

    // Fons: paper
    let fons = CGPath(roundedRect: q, cornerWidth: 22.5 * u, cornerHeight: 22.5 * u, transform: nil)
    g.addPath(fons); g.setFillColor(color(0xF7F2E8)); g.fillPath()
    g.addPath(fons); g.setStrokeColor(color(0xD9D0BE)); g.setLineWidth(max(1, 0.8 * u)); g.strokePath()

    func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: q.minX + x * u, y: q.minY + y * u) }

    // Pentagrama: cinc línies
    let tinta = color(0x2B2A28)
    g.setStrokeColor(tinta); g.setLineWidth(max(1, 1.7 * u)); g.setLineCap(.round)
    let línies: [CGFloat] = [30, 40, 50, 60, 70]
    for y in línies { g.move(to: p(14, y)); g.addLine(to: p(86, y)); g.strokePath() }

    // Dues corxeres unides per una barra
    let nota = color(0xA2412B)
    g.setFillColor(nota); g.setStrokeColor(nota)
    func cap(_ cx: CGFloat, _ cy: CGFloat) {
        g.saveGState()
        g.translateBy(x: p(cx, cy).x, y: p(cx, cy).y); g.rotate(by: 0.42)
        g.fillEllipse(in: CGRect(x: -8.2 * u, y: -5.8 * u, width: 16.4 * u, height: 11.6 * u))
        g.restoreGState()
    }
    cap(36, 35); cap(64, 45)
    g.setLineWidth(3.2 * u); g.setLineCap(.butt)
    g.move(to: p(42.6, 37)); g.addLine(to: p(42.6, 78)); g.strokePath()
    g.move(to: p(70.6, 47)); g.addLine(to: p(70.6, 88)); g.strokePath()
    g.move(to: p(41, 80)); g.addLine(to: p(72.2, 90)); g.addLine(to: p(72.2, 81)); g.addLine(to: p(41, 71)); g.closePath(); g.fillPath()

    return rep
}
func png(_ rep: NSBitmapImageRep) -> Data { rep.representation(using: .png, properties: [:])! }

// icona.png (per a documentació) i .icns (Mac: amb el marge habitual de les icones del sistema)
try png(dibuixa(mida: 512, marge: 0.10)).write(to: ací.appendingPathComponent("icona.png"))
let conjunt = FileManager.default.temporaryDirectory.appendingPathComponent("Arranjaments-\(getpid()).iconset")
try FileManager.default.createDirectory(at: conjunt, withIntermediateDirectories: true)
for (nom, mida) in [("16x16", 16), ("16x16@2x", 32), ("32x32", 32), ("32x32@2x", 64), ("128x128", 128), ("128x128@2x", 256),
                    ("256x256", 256), ("256x256@2x", 512), ("512x512", 512), ("512x512@2x", 1024)] {
    try png(dibuixa(mida: mida, marge: 0.10)).write(to: conjunt.appendingPathComponent("icon_\(nom).png"))
}
let iconutil = Process()
iconutil.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
iconutil.arguments = ["-c", "icns", "-o", ací.appendingPathComponent("Arranjaments.icns").path, conjunt.path]
try iconutil.run(); iconutil.waitUntilExit()
try? FileManager.default.removeItem(at: conjunt)

// .ico (Windows): diverses mides dins d'un sol fitxer, quasi sense marge. Les menudes van en format BMP
// (el que entenen totes les eines de Windows) i la de 256 en PNG.
var ico = Data()
let mides = [16, 24, 32, 48, 64, 256]
func le16(_ v: Int) -> [UInt8] { [UInt8(v & 0xFF), UInt8((v >> 8) & 0xFF)] }
func le32(_ v: Int) -> [UInt8] { [UInt8(v & 0xFF), UInt8((v >> 8) & 0xFF), UInt8((v >> 16) & 0xFF), UInt8((v >> 24) & 0xFF)] }
func bmp(_ rep: NSBitmapImageRep) -> Data {
    let n = rep.pixelsWide
    var d = Data(le32(40) + le32(n) + le32(n * 2) + le16(1) + le16(32) + le32(0) + le32(n * n * 4) + le32(0) + le32(0) + le32(0) + le32(0))
    let px = rep.bitmapData!, fila = rep.bytesPerRow
    for y in stride(from: n - 1, through: 0, by: -1) {
        for x in 0..<n {
            let o = y * fila + x * 4
            let a = Int(px[o + 3])
            // el dibuix porta l'alfa premultiplicat; el format .ico el vol sense premultiplicar
            func c(_ v: UInt8) -> UInt8 { a == 0 ? 0 : UInt8(min(255, Int(v) * 255 / a)) }
            d.append(contentsOf: [c(px[o + 2]), c(px[o + 1]), c(px[o]), UInt8(a)])
        }
    }
    d.append(Data(count: ((n + 31) / 32) * 4 * n))  // màscara buida: la transparència ja va al canal alfa
    return d
}
let imatges = mides.map { $0 == 256 ? png(dibuixa(mida: $0, marge: 0.03)) : bmp(dibuixa(mida: $0, marge: 0.03)) }
ico.append(contentsOf: le16(0) + le16(1) + le16(mides.count))
var posició = 6 + 16 * mides.count
for (mida, imatge) in zip(mides, imatges) {
    ico.append(contentsOf: [UInt8(mida == 256 ? 0 : mida), UInt8(mida == 256 ? 0 : mida), 0, 0] + le16(1) + le16(32) + le32(imatge.count) + le32(posició))
    posició += imatge.count
}
for imatge in imatges { ico.append(imatge) }
try ico.write(to: ací.appendingPathComponent("Arranjaments.ico"))
print("Fet: Arranjaments.icns, Arranjaments.ico, icona.png")
