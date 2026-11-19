// Instal·lar Arranjaments (Mac): una finestra senzilla que executa instalacio/instalar-mac.sh i en mostra el progrés.
// Tota la feina d'instal·lar la fa aquell fitxer; ací només es llig el que escriu (les línies «@@PAS nom estat»
// i «@@FI ok|falla») per a marcar els passos. Es construeix amb construir.sh (swiftc, sense Xcode).
//
// Opcions (per a proves):
//   --auto              comença a instal·lar sense prémer res i ix amb codi 0 (tot bé) o 1 (alguna cosa ha fallat)
//   --prova             no instal·la res: simula els passos per a veure la finestra
//   --prova-error       com --prova, però un pas falla
//   --captura fitxer    guarda una imatge PNG de la finestra en acabar (i una altra «-mig» a mitjan procés)
//   --registre fitxer   guarda en un fitxer de text tot el que ha escrit l'instal·lador
//   --carpeta ruta      carpeta del projecte (si no, la carpeta on és esta aplicació o, si no n'hi ha, el projecte que
//                       porta dins de l'aplicació: Contents/Resources/projecte.tar.gz, com a «Arranjaments-Mac.dmg»)
import AppKit
import SwiftUI

let urlOneDrive = URL(string: "https://apps.apple.com/app/onedrive/id823766827")!
let urlAjuda = URL(string: "https://github.com/Carlescamarasa/arranjaments#manual")!

// MARK: - Opcions

struct Opcions {
    var auto = false, prova = false, provaError = false, provaSenseOneDrive = false
    var captura: String?
    var registre: String?
    var carpeta: String?

    init(_ args: [String]) {
        var i = 1
        while i < args.count {
            switch args[i] {
            case "--auto": auto = true
            case "--prova": prova = true
            case "--prova-error": prova = true; provaError = true
            case "--prova-sense-onedrive": prova = true; provaSenseOneDrive = true
            case "--captura": i += 1; if i < args.count { captura = args[i] }
            case "--registre": i += 1; if i < args.count { registre = args[i] }
            case "--carpeta": i += 1; if i < args.count { carpeta = args[i] }
            default: break
            }
            i += 1
        }
    }
}

// MARK: - Carpeta del projecte

/// Quan una aplicació baixada d'internet s'obri per primera vegada, macOS pot executar-la des d'una còpia
/// temporal en un altre lloc («App Translocation»). Esta funció torna la ruta de veritat.
func rutaOriginal(_ url: URL) -> URL {
    guard let seguretat = dlopen("/System/Library/Frameworks/Security.framework/Security", RTLD_LAZY) else { return url }
    defer { dlclose(seguretat) }
    typealias EsTraslladada = @convention(c) (CFURL, UnsafeMutablePointer<Bool>, UnsafeMutablePointer<Unmanaged<CFError>?>?) -> Bool
    typealias Original = @convention(c) (CFURL, UnsafeMutablePointer<Unmanaged<CFError>?>?) -> Unmanaged<CFURL>?
    guard let s1 = dlsym(seguretat, "SecTranslocateIsTranslocatedURL"),
          let s2 = dlsym(seguretat, "SecTranslocateCreateOriginalPathForURL") else { return url }
    let esTraslladada = unsafeBitCast(s1, to: EsTraslladada.self)
    let original = unsafeBitCast(s2, to: Original.self)
    var traslladada = false
    guard esTraslladada(url as CFURL, &traslladada, nil), traslladada,
          let resultat = original(url as CFURL, nil) else { return url }
    return resultat.takeRetainedValue() as URL
}

func teInstalador(_ carpeta: URL) -> Bool {
    FileManager.default.fileExists(atPath: carpeta.appendingPathComponent("instalacio/instalar-mac.sh").path)
}

func carpetaDelProjecte(_ opcions: Opcions) -> URL? {
    if let c = opcions.carpeta {
        let u = URL(fileURLWithPath: c)
        return teInstalador(u) ? u : nil
    }
    let c = rutaOriginal(Bundle.main.bundleURL).deletingLastPathComponent()
    return teInstalador(c) ? c : nil
}

/// El projecte que porta l'aplicació dins (a «Arranjaments-Mac.dmg»). Una aplicació oberta des d'un DMG viu en un volum
/// de només lectura: per això no s'executa res des d'ací, sinó que primer es descomprimeix a la carpeta de dades de l'usuari.
func projecteIntern() -> URL? {
    Bundle.main.url(forResource: "projecte", withExtension: "tar.gz")
}

/// La versió que porta el paquet (fitxer VERSION): de dins del tar.gz de l'aplicació o, si és al costat del projecte, de la carpeta.
/// Es llig en el moment, així mai queda desfasada. Si no es pot saber, no es mostra res.
func versioText() -> String? {
    var text: String?
    if let tgz = projecteIntern() {
        let t = Process()
        t.executableURL = URL(fileURLWithPath: "/usr/bin/tar")
        t.arguments = ["-xzOf", tgz.path, "VERSION"]
        let canal = Pipe()
        t.standardOutput = canal
        t.standardError = FileHandle.nullDevice
        if (try? t.run()) != nil {
            let dades = canal.fileHandleForReading.readDataToEndOfFile()
            t.waitUntilExit()
            if t.terminationStatus == 0 { text = String(data: dades, encoding: .utf8) }
        }
    } else {
        let c = rutaOriginal(Bundle.main.bundleURL).deletingLastPathComponent()
        text = try? String(contentsOf: c.appendingPathComponent("VERSION"), encoding: .utf8)
    }
    let net = (text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    return net.isEmpty ? nil : "Versió " + net
}

func carpetaTemporal() -> URL {
    FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Arranjaments/staging")
}

// MARK: - Model

/// Barra de progrés pròpia: el ProgressView del sistema es torna grisa quan la finestra no està activa
/// (per exemple en acabar, amb el mode fosc) i no es veu que ha acabat. Esta sempre és verda (roja si hi ha error).
struct BarraProgres: View {
    let valor: Double
    let error: Bool
    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Capsule().fill(Color.secondary.opacity(0.25))
                Capsule().fill(error ? Color.red : Color.green)
                    .frame(width: max(0, min(1, valor)) * g.size.width)
            }
        }
        .frame(height: 8)
        .accessibilityElement()
        .accessibilityLabel("Progrés de la instal·lació")
        .accessibilityValue("\(Int(max(0, min(1, valor)) * 100)) per cent")
    }
}

enum EstatPas { case pendent, enMarxa, fet, falla }

struct Pas: Identifiable {
    let id: String
    let titol: String
    let detall: String
    var opcional = false     // un pas opcional mai fa fallar la instal·lació
    var estat: EstatPas = .pendent
}

enum Fase { case inici, installant, acabat, error, senseCarpeta }

final class Model: ObservableObject {
    @Published var passos: [Pas] = [
        Pas(id: "uv", titol: "Preparació", detall: "El programa que prepara les eines musicals"),
        Pas(id: "opencode", titol: "OpenCode", detall: "L'aplicació amb la qual parles amb l'ajudant"),
        Pas(id: "musescore", titol: "MuseScore", detall: "Per a revisar partitures i fer PDF"),
        Pas(id: "eines", titol: "Eines musicals", detall: "Queden guardades dins de l'ordinador, com les de qualsevol aplicació"),
        Pas(id: "carpeta", titol: "Carpeta de treball", detall: "Documents, Arranjaments: amb «entrada» i «eixida» per a les partitures"),
        Pas(id: "icona", titol: "Icona a l'Escriptori", detall: "Per a obrir Arranjaments amb doble clic"),
        Pas(id: "onedrive", titol: "OneDrive (opcional)", detall: "Per a la biblioteca compartida de l'escola", opcional: true),
    ]
    @Published var fase: Fase = .inici
    @Published var progres: Double = 0
    @Published var estat = ""
    @Published var registre = ""
    @Published var detalls = false { didSet { canviDeMida?() } }
    @Published var missatgeError = ""
    @Published var senseOneDrive = false     // l'instal·lador ha dit que OneDrive no hi és (@@NOTA onedrive): el panell final ofereix el botó

    let opcions: Opcions
    var carpeta: URL?
    let projecte: URL?          // el projecte de dins de l'aplicació, si no hi ha cap carpeta al costat
    var usaProjecte = false
    var canviDeMida: (() -> Void)?
    var enAcabar: ((Bool) -> Void)?
    var aMitges: (() -> Void)?

    private var proces: Process?
    private var pendent = Data()
    private var finalRebut: Bool?
    private var comprovacio: EstatPas = .pendent
    private var avisatAMitges = false

    init(opcions: Opcions) {
        self.opcions = opcions
        carpeta = carpetaDelProjecte(opcions)
        projecte = projecteIntern()
        usaProjecte = carpeta == nil && projecte != nil
        if carpeta == nil && projecte == nil && !opcions.prova { fase = .senseCarpeta }
    }

    var installant: Bool { fase == .installant }

    // MARK: Lectura del que escriu l'instal·lador

    /// Una línia del registre. Les que comencen per «@@» són avisos de progrés i no es mostren.
    func rep(linia: String) {
        if linia.hasPrefix("@@") {
            let parts = linia.dropFirst(2).split(separator: " ").map(String.init)
            if parts.count >= 3, parts[0] == "PAS" { marca(pas: parts[1], estat: parts[2]) }
            else if parts.count >= 2, parts[0] == "FI" { finalRebut = (parts[1] == "ok") }
            else if parts.count >= 2, parts[0] == "NOTA", parts[1] == "onedrive" { senseOneDrive = true }
            return
        }
        registre += linia + "\n"
        var neta = linia.trimmingCharacters(in: .whitespaces)
        for marca in ["[fet]", "[falta]"] where neta.hasPrefix(marca) { neta = neta.dropFirst(marca.count).trimmingCharacters(in: .whitespaces) }
        if !neta.isEmpty && !neta.hasPrefix("==") { estat = neta }
    }

    private func marca(pas id: String, estat text: String) {
        let nou: EstatPas
        switch text {
        case "inici": nou = .enMarxa
        case "ok": nou = .fet
        default: nou = .falla
        }
        if id == "final" { comprovacio = nou }
        else if let i = passos.firstIndex(where: { $0.id == id }) { passos[i].estat = nou }
        // la barra: cada pas (i la comprovació final) val una part; el que està en marxa, mitja
        let estats = passos.map(\.estat) + [comprovacio]
        let fets = estats.reduce(0.0) { $0 + ($1 == .fet || $1 == .falla ? 1 : ($1 == .enMarxa ? 0.5 : 0)) }
        progres = fets / Double(estats.count)
        if id == "musescore" && nou == .enMarxa && !avisatAMitges { avisatAMitges = true; aMitges?() }
    }

    private func rep(dades: Data) {
        pendent.append(dades)
        while let salt = pendent.firstIndex(of: 0x0A) {
            let tros = pendent.subdata(in: pendent.startIndex..<salt)
            pendent.removeSubrange(pendent.startIndex...salt)
            var text = String(decoding: tros, as: UTF8.self)
            // les barres de progrés de terminal reescriuen la línia amb un retorn de carro: ens quedem l'últim tros
            if text.hasSuffix("\r") { text.removeLast() }
            if let r = text.lastIndex(of: "\r") { text = String(text[text.index(after: r)...]) }
            rep(linia: text)
        }
    }

    // MARK: Instal·lació

    func comenca() {
        guard fase != .installant else { return }
        for i in passos.indices { passos[i].estat = .pendent }
        comprovacio = .pendent; finalRebut = nil; progres = 0; pendent = Data()
        registre = ""; estat = "Començant..."; missatgeError = ""; senseOneDrive = false
        fase = .installant
        canviDeMida?()
        if opcions.prova { simula(); return }
        if usaProjecte, let projecte = projecte {
            estat = "Preparant els fitxers..."
            do { carpeta = try extrauProjecte(projecte) } catch {
                rep(linia: "No s'han pogut preparar els fitxers de la instal·lació: \(error.localizedDescription)")
                acaba(codi: 1)
                return
            }
        }
        guard let carpeta = carpeta else { fase = .senseCarpeta; return }

        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [carpeta.appendingPathComponent("instalacio/instalar-mac.sh").path, "--sense-preguntes"]
        p.currentDirectoryURL = carpeta
        var entorn = ProcessInfo.processInfo.environment
        entorn["ARRANJAMENTS_PROGRES"] = "1"
        if entorn["LANG"] == nil && entorn["LC_ALL"] == nil { entorn["LC_CTYPE"] = "UTF-8" }
        p.environment = entorn
        let canonada = Pipe()
        p.standardOutput = canonada
        p.standardError = canonada
        p.standardInput = FileHandle.nullDevice
        canonada.fileHandleForReading.readabilityHandler = { [weak self] f in
            let dades = f.availableData
            guard !dades.isEmpty else { return }
            DispatchQueue.main.async { self?.rep(dades: dades) }
        }
        p.terminationHandler = { [weak self] acabat in
            // un moment de marge perquè arribe l'últim text abans de tancar
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                canonada.fileHandleForReading.readabilityHandler = nil
                self?.acaba(codi: acabat.terminationStatus)
            }
        }
        do { try p.run(); proces = p } catch {
            rep(linia: "No s'ha pogut engegar l'instal·lador: \(error.localizedDescription)")
            acaba(codi: 1)
        }
    }

    /// Descomprimeix el projecte de dins de l'aplicació a una carpeta temporal de la carpeta de dades (sempre de nou).
    private func extrauProjecte(_ arxiu: URL) throws -> URL {
        let desti = carpetaTemporal()
        let fm = FileManager.default
        try? fm.removeItem(at: desti)
        try fm.createDirectory(at: desti, withIntermediateDirectories: true)
        let t = Process()
        t.executableURL = URL(fileURLWithPath: "/usr/bin/tar")
        t.arguments = ["-xzf", arxiu.path, "-C", desti.path]
        t.standardInput = FileHandle.nullDevice
        try t.run()
        t.waitUntilExit()
        guard t.terminationStatus == 0, teInstalador(desti) else {
            throw NSError(domain: "Arranjaments", code: Int(t.terminationStatus), userInfo: [NSLocalizedDescriptionKey: "el fitxer de l'aplicació està trencat; torna a baixar-lo"])
        }
        return desti
    }

    private func acaba(codi: Int32) {
        if usaProjecte {   // la còpia temporal ja no cal (la instal·lació se n'ha endut el que li feia falta)
            try? FileManager.default.removeItem(at: carpetaTemporal())
            carpeta = nil
        }
        if !pendent.isEmpty { rep(dades: Data([0x0A])) }
        proces = nil
        let be = codi == 0 && finalRebut == true && !passos.contains { $0.estat != .fet && !$0.opcional }
        for i in passos.indices where passos[i].estat == .enMarxa { passos[i].estat = .falla }
        if be {
            progres = 1
            estat = ""
            fase = .acabat
        } else {
            let fallats = passos.filter { $0.estat == .falla && !$0.opcional }.map(\.titol)
            if !fallats.isEmpty {
                missatgeError = "Ha faltat: " + fallats.joined(separator: ", ") + "."
            } else if finalRebut == nil {
                missatgeError = "L'instal·lador s'ha aturat abans d'acabar."
            } else {
                missatgeError = "La comprovació final ha trobat algun problema."
            }
            fase = .error
        }
        canviDeMida?()
        if let ruta = opcions.registre {
            try? (registre + "RESULTAT: " + (be ? "tot a punt" : missatgeError) + "\n").write(toFile: ruta, atomically: true, encoding: .utf8)
        }
        enAcabar?(be)
    }

    func atura() {
        proces?.terminationHandler = nil
        proces?.terminate()
        proces = nil
    }

    /// Mode de prova: les mateixes línies que escriuria l'instal·lador, però sense instal·lar res.
    private func simula() {
        var linies: [String] = []
        for (n, p) in passos.enumerated() {
            let falla = opcions.provaError && p.id == "musescore"
            linies += ["@@PAS \(p.id) inici", "", "== \(n + 1). \(p.titol) (prova) =="]
            linies += falla ? ["  [falta]  No he pogut instal·lar \(p.titol) automàticament (prova)."] : ["  [fet]    \(p.titol) (prova, no s'ha instal·lat res)"]
            if p.id == "onedrive" && opcions.provaSenseOneDrive { linies += ["@@NOTA onedrive"] }
            linies += ["@@PAS \(p.id) \(falla ? "falla" : "ok")"]
        }
        linies += ["@@PAS final inici", "", "== Comprovació final (prova) ==", "@@PAS final \(opcions.provaError ? "falla" : "ok")",
                   "@@FI \(opcions.provaError ? "falla 1" : "ok")"]
        var espera = 0.0
        for l in linies {
            espera += l.hasPrefix("@@PAS") && l.hasSuffix("inici") ? 0.15 : 0.3
            DispatchQueue.main.asyncAfter(deadline: .now() + espera) { [weak self] in self?.rep(linia: l) }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + espera + 0.4) { [weak self] in
            self?.acaba(codi: self?.opcions.provaError == true ? 1 : 0)
        }
    }

    // MARK: Accions de la finestra

    func obriArranjaments() {
        guard !opcions.prova else { return }
        let icona = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Desktop/Arranjaments.app")
        NSWorkspace.shared.open(icona)
        NSApp.terminate(nil)
    }

    func triaCarpeta() {
        let tria = NSOpenPanel()
        tria.canChooseDirectories = true
        tria.canChooseFiles = false
        tria.message = "Tria la carpeta d'Arranjaments (on veus el fitxer README.md)."
        tria.prompt = "Triar"
        guard tria.runModal() == .OK, let u = tria.url else { return }
        if teInstalador(u) { carpeta = u; fase = .inici; canviDeMida?() }
        else {
            let avis = NSAlert()
            avis.messageText = "Esta no és la carpeta d'Arranjaments."
            avis.informativeText = "La carpeta bona és aquella on veus el fitxer README.md i la carpeta «instalacio»."
            avis.runModal()
        }
    }
}

// MARK: - Vistes

struct Indicador: View {
    let estat: EstatPas
    var body: some View {
        Group {
            switch estat {
            case .pendent: Image(systemName: "circle").foregroundColor(Color.secondary.opacity(0.5))
            case .enMarxa: ProgressView().controlSize(.small)
            case .fet: Image(systemName: "checkmark.circle.fill").foregroundColor(.green)
            case .falla: Image(systemName: "exclamationmark.circle.fill").foregroundColor(.orange)
            }
        }
        .font(.system(size: 17))
        .frame(width: 22, height: 22)
    }
}

struct Registre: NSViewRepresentable {
    let text: String
    func makeNSView(context: Context) -> NSScrollView {
        let vista = NSTextView.scrollableTextView()
        if let t = vista.documentView as? NSTextView {
            t.isEditable = false
            t.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
            t.textContainerInset = NSSize(width: 6, height: 6)
            t.setAccessibilityLabel("Detalls de la instal·lació")
        }
        vista.borderType = .bezelBorder
        return vista
    }
    func updateNSView(_ vista: NSScrollView, context: Context) {
        guard let t = vista.documentView as? NSTextView, t.string != text else { return }
        t.string = text
        t.scrollToEndOfDocument(nil)
    }
}

struct Contingut: View {
    @ObservedObject var model: Model

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .center, spacing: 14) {
                Image(nsImage: NSApp.applicationIconImage).resizable().frame(width: 64, height: 64)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Instal·lar Arranjaments").font(.system(size: 22, weight: .semibold))
                    Text("Prepara este ordinador per a fer arranjaments amb l'ajudant. Només s'instal·la el que falta i pot tardar uns minuts.")
                        .foregroundColor(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    if let v = versioText() {
                        Text(v).font(.caption).foregroundColor(.secondary)
                    }
                }
            }

            VStack(alignment: .leading, spacing: 9) {
                ForEach(model.passos) { pas in
                    HStack(alignment: .center, spacing: 10) {
                        Indicador(estat: pas.estat)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(pas.titol).fontWeight(.medium)
                            Text(pas.detall).font(.callout).foregroundColor(.secondary)
                        }
                    }
                    .accessibilityElement(children: .combine)
                }
            }
            .padding(.leading, 4)

            if model.fase == .installant || model.fase == .acabat || model.fase == .error {
                VStack(alignment: .leading, spacing: 6) {
                    BarraProgres(valor: model.progres, error: model.fase == .error)
                    if model.fase == .installant {
                        Text(model.estat.isEmpty ? " " : model.estat)
                            .font(.callout).foregroundColor(.secondary)
                            .lineLimit(1).truncationMode(.middle)
                    }
                }
            }

            resultat

            if model.fase != .inici && model.fase != .senseCarpeta {
                VStack(alignment: .leading, spacing: 8) {
                    Button(action: { model.detalls.toggle() }) {
                        HStack(spacing: 4) {
                            Image(systemName: model.detalls ? "chevron.down" : "chevron.right").font(.caption.weight(.semibold))
                            Text("Veure detalls")
                        }
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.secondary)
                    if model.detalls { Registre(text: model.registre).frame(height: 170) }
                }
            }

            botons
        }
        .padding(24)
        .frame(width: 500)
    }

    @ViewBuilder var resultat: some View {
        switch model.fase {
        case .acabat:
            VStack(alignment: .leading, spacing: 3) {
                Text("Tot a punt.").font(.headline)
                Text("Obri Arranjaments a l'Escriptori.")
                Text("Les teues partitures aniran a la carpeta Arranjaments de Documents. La carpeta des d'on has instal·lat ja no cal.")
                    .foregroundColor(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Text("Per a la biblioteca compartida (opcional): 1) obri OneDrive i entra amb el compte de l'escola (@edu.gva.es). 2) Obri l'enllaç de la biblioteca que t'ha passat una companya i prem «Afegeix una drecera a Els meus fitxers» (la carpeta ha de dir-se «Biblioteca d'arranjaments»). 3) Espera uns minuts. Quan el Mac pregunte si pot accedir als fitxers de OneDrive, prem «Permet».")
                    .foregroundColor(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 6)
                if model.senseOneDrive {
                    Text("Ara mateix no tens OneDrive en este Mac. Pots instal·lar-lo des de l'App Store (no demana contrasenya) o, si prefereixes, baixar l'instal·lador de Microsoft a microsoft.com/microsoft-365/onedrive/download.")
                        .foregroundColor(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, 4)
                }
            }
        case .error:
            VStack(alignment: .leading, spacing: 3) {
                Text("No s'ha pogut instal·lar tot.").font(.headline)
                Text(model.missatgeError + " Pots tornar-ho a provar, només es fa el que falta. Si continua fallant, tens els passos per a fer-ho a mà.")
                    .fixedSize(horizontal: false, vertical: true)
            }
        case .senseCarpeta:
            VStack(alignment: .leading, spacing: 3) {
                Text("No trobe la carpeta d'Arranjaments.").font(.headline)
                Text("Esta aplicació ha d'estar dins de la carpeta del projecte, al costat del fitxer README.md. Si l'has moguda, torna-la al seu lloc o tria la carpeta.")
                    .fixedSize(horizontal: false, vertical: true)
            }
        default: EmptyView()
        }
    }

    @ViewBuilder var botons: some View {
        HStack {
            switch model.fase {
            case .inici:
                Spacer()
                Button("Tancar") { NSApp.terminate(nil) }
                Button("Instal·lar") { model.comenca() }.keyboardShortcut(.defaultAction)
            case .installant:
                Spacer()
                Button("Instal·lant...") {}.disabled(true)
            case .acabat:
                Spacer()
                if model.senseOneDrive {
                    Button("Instal·la OneDrive") { NSWorkspace.shared.open(urlOneDrive) }
                }
                Button("Tancar") { NSApp.terminate(nil) }
                Button("Obrir Arranjaments") { model.obriArranjaments() }.keyboardShortcut(.defaultAction)
            case .error:
                Button("Instal·lació a mà") { NSWorkspace.shared.open(urlAjuda) }
                Spacer()
                Button("Tancar") { NSApp.terminate(nil) }
                Button("Tornar-ho a provar") { model.comenca() }.keyboardShortcut(.defaultAction)
            case .senseCarpeta:
                Spacer()
                Button("Tancar") { NSApp.terminate(nil) }
                Button("Triar la carpeta...") { model.triaCarpeta() }.keyboardShortcut(.defaultAction)
            }
        }
    }
}

// MARK: - Aplicació

final class Delegat: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let opcions = Opcions(CommandLine.arguments)
    var model: Model!
    var finestra: NSWindow!
    var vista: NSHostingView<Contingut>!

    func applicationDidFinishLaunching(_ avis: Notification) {
        model = Model(opcions: opcions)
        vista = NSHostingView(rootView: Contingut(model: model))
        finestra = NSWindow(contentRect: NSRect(origin: .zero, size: vista.fittingSize),
                            styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        finestra.title = "Instal·lar Arranjaments"
        finestra.contentView = vista
        finestra.delegate = self
        finestra.isReleasedWhenClosed = false
        finestra.center()
        model.canviDeMida = { [weak self] in DispatchQueue.main.async { self?.ajustaMida() } }
        model.aMitges = { [weak self] in
            guard let self = self, let ruta = self.opcions.captura else { return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { self.captura(a: ruta.replacingOccurrences(of: ".png", with: "-mig.png")) }
        }
        model.enAcabar = { [weak self] be in
            guard let self = self else { return }
            guard self.opcions.auto || self.opcions.captura != nil else { return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                if let ruta = self.opcions.captura { self.captura(a: ruta) }
                if self.opcions.auto {
                    print(self.model.registre)
                    print(be ? "RESULTAT: tot a punt" : "RESULTAT: \(self.model.missatgeError)")
                    exit(be ? 0 : 1)
                }
            }
        }
        creaMenu()
        if opcions.auto {
            // sense robar el focus: és una prova automàtica
            finestra.orderFront(nil)
            if model.fase == .senseCarpeta { print("RESULTAT: no trobe la carpeta del projecte"); exit(2) }
            model.comenca()
        } else {
            finestra.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
        }
    }

    func ajustaMida() {
        vista.layoutSubtreeIfNeeded()
        let nova = vista.fittingSize
        var marc = finestra.frameRect(forContentRect: NSRect(origin: .zero, size: nova))
        marc.origin = NSPoint(x: finestra.frame.minX, y: finestra.frame.maxY - marc.height)
        finestra.setFrame(marc, display: true, animate: !opcions.auto)
    }

    func captura(a ruta: String) {
        ajustaMida()
        // deixa que la finestra acabe de dibuixar l'últim canvi (si no, la captura pot portar peces de l'estat anterior)
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.4))
        vista.layoutSubtreeIfNeeded()
        finestra.displayIfNeeded()
        // el marc sencer de la finestra (amb la barra de títol i el fons), no només el contingut
        guard let marc = vista.superview, let rep = marc.bitmapImageRepForCachingDisplay(in: marc.bounds) else { return }
        marc.cacheDisplay(in: marc.bounds, to: rep)
        try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: ruta))
    }

    func creaMenu() {
        let principal = NSMenu()
        let app = NSMenuItem(); principal.addItem(app)
        app.submenu = NSMenu()
        app.submenu?.addItem(withTitle: "Eixir d'Instal·lar Arranjaments", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let edicio = NSMenuItem(); principal.addItem(edicio)
        edicio.submenu = NSMenu(title: "Edició")
        edicio.submenu?.addItem(withTitle: "Copiar", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edicio.submenu?.addItem(withTitle: "Seleccionar-ho tot", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        NSApp.mainMenu = principal
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { true }

    func applicationShouldTerminate(_ app: NSApplication) -> NSApplication.TerminateReply {
        guard model.installant, !opcions.prova else { return .terminateNow }
        let avis = NSAlert()
        avis.messageText = "La instal·lació encara no ha acabat."
        avis.informativeText = "Si ixes ara, quedarà a mitges. Podràs tornar a obrir l'instal·lador més avant: només fa el que falta."
        avis.addButton(withTitle: "Continuar instal·lant")
        avis.addButton(withTitle: "Eixir")
        if avis.runModal() == .alertFirstButtonReturn { return .terminateCancel }
        model.atura()
        return .terminateNow
    }

    func windowShouldClose(_ finestra: NSWindow) -> Bool {
        NSApp.terminate(nil)
        return false
    }
}

let aplicacio = NSApplication.shared
let delegat = Delegat()
aplicacio.delegate = delegat
aplicacio.setActivationPolicy(.regular)
aplicacio.run()
