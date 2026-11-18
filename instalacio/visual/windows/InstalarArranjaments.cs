// Instal·lar Arranjaments (Windows): una finestra senzilla que executa instalacio\instalar-windows.ps1 (amagat)
// i en mostra el progrés. Tota la feina d'instal·lar la fa aquell fitxer; ací només es llig el que escriu
// (les línies «@@PAS nom estat» i «@@FI ok|falla») per a marcar els passos.
// Es construeix amb construir.ps1: usa el compilador de C# que ja porta Windows (.NET Framework 4.8),
// per això el codi és C# 5 i el programa ocupa molt poc i no necessita instal·lar res.
//
// Opcions (per a proves):
//   --auto              comença a instal·lar sense prémer res i ix amb codi 0 (tot bé) o 1 (alguna cosa ha fallat)
//   --prova             no instal·la res: simula els passos per a veure la finestra
//   --prova-error       com --prova, però un pas falla
//   --captura fitxer    guarda una imatge PNG de la finestra en acabar (i una altra «-mig» a mitjan procés)
//   --registre fitxer   guarda en un fitxer de text tot el que ha escrit l'instal·lador
//   --carpeta ruta      carpeta del projecte (si no, la carpeta on és este programa)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Instal·lar Arranjaments")]
[assembly: AssemblyProduct("Arranjaments")]
[assembly: AssemblyDescription("Instal·lador visual d'Arranjaments")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace Arranjaments
{
    enum EstatPas { Pendent, EnMarxa, Fet, Falla }
    enum Fase { Inici, Installant, Acabat, Error, SenseCarpeta }

    class Pas
    {
        public string Id, Titol, Detall;
        public EstatPas Estat = EstatPas.Pendent;
        public Pas(string id, string titol, string detall) { Id = id; Titol = titol; Detall = detall; }
    }

    class Opcions
    {
        public bool Auto, Prova, ProvaError;
        public string Captura, Registre, Carpeta;
        public Opcions(string[] args)
        {
            for (int i = 0; i < args.Length; i++)
            {
                string a = args[i];
                if (a == "--auto") Auto = true;
                else if (a == "--prova") Prova = true;
                else if (a == "--prova-error") { Prova = true; ProvaError = true; }
                else if (a == "--captura" && i + 1 < args.Length) Captura = args[++i];
                else if (a == "--registre" && i + 1 < args.Length) Registre = args[++i];
                else if (a == "--carpeta" && i + 1 < args.Length) Carpeta = args[++i];
            }
        }
    }

    // Panell que es dibuixa sense parpellejar
    class Llista : Panel
    {
        public Llista() { DoubleBuffered = true; ResizeRedraw = true; }
    }

    class Finestra : Form
    {
        const string UrlAjuda = "https://github.com/Carlescamarasa/arranjaments#manual";

        readonly Opcions opcions;
        readonly List<Pas> passos = new List<Pas>();
        Fase fase = Fase.Inici;
        string carpeta;
        EstatPas comprovacio = EstatPas.Pendent;
        bool? finalRebut;
        string missatgeError = "";
        readonly StringBuilder registre = new StringBuilder();
        Process proces;
        bool avisatAMitges;
        public int CodiEixida;

        float f = 1f;  // escala de la pantalla (1 = 96 ppp)
        int angle;
        PictureBox imatge;
        Label titol, frase, estat, resultatTitol, resultatText;
        Llista llista;
        ProgressBar barra;
        LinkLabel detalls;
        TextBox text;
        Button boto1, boto2, botoAjuda;
        System.Windows.Forms.Timer rellotge;
        Font lletraTitolPas, lletraDetall;

        int S(int v) { return (int)Math.Round(v * f); }

        public Finestra(Opcions o)
        {
            opcions = o;
            passos.Add(new Pas("uv", "uv", "El programa que prepara les eines musicals"));
            passos.Add(new Pas("opencode", "OpenCode", "L'aplicació amb la qual parles amb l'ajudant"));
            passos.Add(new Pas("musescore", "MuseScore", "Per a revisar partitures i fer PDF"));
            passos.Add(new Pas("eines", "Eines musicals", "Queden guardades dins de l'ordinador, com les de qualsevol aplicació"));
            passos.Add(new Pas("carpeta", "Carpeta de treball", "Documents, Arranjaments: amb «entrada» i «eixida» per a les partitures"));
            passos.Add(new Pas("icona", "Icona a l'Escriptori", "Per a obrir Arranjaments amb doble clic"));

            carpeta = o.Carpeta != null ? o.Carpeta : Path.GetDirectoryName(Application.ExecutablePath);
            if (!TeInstalador(carpeta)) { carpeta = null; if (!o.Prova) fase = Fase.SenseCarpeta; }

            Text = "Instal·lar Arranjaments";
            Font = new Font("Segoe UI", 9f);
            BackColor = SystemColors.Window;
            ForeColor = SystemColors.WindowText;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.None;
            using (Graphics g = CreateGraphics()) { f = g.DpiX / 96f; }
            lletraTitolPas = new Font("Segoe UI Semibold", 9.75f);
            lletraDetall = new Font("Segoe UI", 9f);

            Icon menuda = CarregaIcona(32);
            if (menuda != null) Icon = menuda;

            imatge = new PictureBox();
            imatge.SizeMode = PictureBoxSizeMode.Zoom;
            foreach (int mida in new int[] { 256, 64 })
            {
                try { Icon gran = CarregaIcona(mida); if (gran != null) { imatge.Image = gran.ToBitmap(); break; } } catch { }
            }
            Controls.Add(imatge);

            titol = new Label();
            titol.Text = "Instal·lar Arranjaments";
            titol.Font = new Font("Segoe UI Semibold", 15f);
            titol.AutoSize = true;
            titol.UseMnemonic = false;
            Controls.Add(titol);

            frase = NovaEtiqueta("Prepara este ordinador per a fer arranjaments amb l'ajudant. Només s'instal·la el que falta i pot tardar uns minuts.");
            frase.ForeColor = SystemColors.GrayText;

            llista = new Llista();
            llista.Paint += PintaLlista;
            Controls.Add(llista);

            barra = new ProgressBar();
            barra.Minimum = 0; barra.Maximum = 1000; barra.Style = ProgressBarStyle.Continuous;
            Controls.Add(barra);

            estat = new Label();
            estat.AutoEllipsis = true;
            estat.UseMnemonic = false;
            estat.ForeColor = SystemColors.GrayText;
            Controls.Add(estat);

            resultatTitol = new Label();
            resultatTitol.Font = new Font("Segoe UI Semibold", 10.5f);
            resultatTitol.AutoSize = true;
            resultatTitol.UseMnemonic = false;
            Controls.Add(resultatTitol);
            resultatText = NovaEtiqueta("");

            detalls = new LinkLabel();
            detalls.Text = "Veure detalls";
            detalls.AutoSize = true;
            detalls.LinkBehavior = LinkBehavior.HoverUnderline;
            detalls.LinkClicked += delegate { text.Visible = !text.Visible; detalls.Text = text.Visible ? "Amagar detalls" : "Veure detalls"; Colloca(); };
            Controls.Add(detalls);

            text = new TextBox();
            text.Multiline = true; text.ReadOnly = true; text.ScrollBars = ScrollBars.Vertical; text.WordWrap = true;
            text.Font = new Font("Consolas", 9f);
            text.BackColor = SystemColors.Window;
            text.Visible = false;
            text.AccessibleName = "Detalls de la instal·lació";
            Controls.Add(text);

            botoAjuda = NouBoto(); boto1 = NouBoto(); boto2 = NouBoto();
            botoAjuda.Text = "Instal·lació a mà";
            botoAjuda.Click += delegate { Obri(UrlAjuda); };
            boto1.Click += delegate { Boto1(); };
            boto2.Click += delegate { Boto2(); };

            rellotge = new System.Windows.Forms.Timer();
            rellotge.Interval = 60;
            rellotge.Tick += delegate { angle = (angle + 24) % 360; if (fase == Fase.Installant) llista.Invalidate(); };

            FormClosing += AlTancar;
            Colloca();
        }

        Label NovaEtiqueta(string t)
        {
            Label l = new Label();
            l.Text = t;
            l.UseMnemonic = false;
            Controls.Add(l);
            return l;
        }

        Button NouBoto()
        {
            Button b = new Button();
            b.FlatStyle = FlatStyle.System;
            b.UseMnemonic = false;
            Controls.Add(b);
            return b;
        }

        static Icon CarregaIcona(int mida)
        {
            try
            {
                using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("Arranjaments.ico"))
                {
                    if (s == null) return null;
                    return new Icon(s, new Size(mida, mida));
                }
            }
            catch { return null; }
        }

        static bool TeInstalador(string c)
        {
            return c != null && File.Exists(Path.Combine(Path.Combine(c, "instalacio"), "instalar-windows.ps1"));
        }

        // ---------------------------------------------------------------- Disposició de la finestra

        void Colloca()
        {
            int ample = S(500), marge = S(24), dins = ample - 2 * marge, y = S(22);
            SuspendLayout();

            imatge.SetBounds(marge, y, S(56), S(56));
            int xText = marge + S(56) + S(14), ampleText = ample - marge - xText;
            titol.Location = new Point(xText - S(3), y - S(4));
            int altFrase = frase.GetPreferredSize(new Size(ampleText, 0)).Height;
            frase.SetBounds(xText, y + S(28), ampleText, altFrase);
            y = Math.Max(y + S(56), frase.Bottom) + S(18);

            llista.SetBounds(marge, y, dins, passos.Count * S(42));
            y = llista.Bottom + S(10);

            bool ambBarra = fase == Fase.Installant || fase == Fase.Acabat || fase == Fase.Error;
            barra.Visible = ambBarra;
            estat.Visible = fase == Fase.Installant;
            if (ambBarra) { barra.SetBounds(marge, y, dins, S(8)); y = barra.Bottom + S(8); }
            if (estat.Visible) { estat.SetBounds(marge, y, dins, S(18)); y = estat.Bottom + S(8); }

            string rt = "", rx = "";
            if (fase == Fase.Acabat) { rt = "Tot a punt."; rx = "Obri Arranjaments a l'Escriptori.\n\nLes teues partitures aniran a la carpeta Arranjaments de Documents. La carpeta des d'on has instal·lat ja no cal."; }
            else if (fase == Fase.Error)
            {
                rt = "No s'ha pogut instal·lar tot.";
                rx = missatgeError + " Pots tornar-ho a provar, només es fa el que falta. Si continua fallant, tens els passos per a fer-ho a mà.";
            }
            else if (fase == Fase.SenseCarpeta)
            {
                rt = "No trobe la carpeta d'Arranjaments.";
                rx = "Si has obert este programa des de dins del ZIP, primer cal descomprimir-lo: clic dret al ZIP, «Extreure-ho tot», i obri l'instal·lador des de la carpeta nova. Este programa ha d'estar al costat del fitxer README.md.";
            }
            resultatTitol.Visible = resultatText.Visible = rt != "";
            if (rt != "")
            {
                y += S(6);
                resultatTitol.Text = rt;
                resultatTitol.Location = new Point(marge - S(2), y);
                y = resultatTitol.Bottom + S(2);
                resultatText.Text = rx;
                resultatText.SetBounds(marge, y, dins, resultatText.GetPreferredSize(new Size(dins, 0)).Height);
                y = resultatText.Bottom + S(10);
            }

            bool ambDetalls = fase != Fase.Inici && fase != Fase.SenseCarpeta;
            detalls.Visible = ambDetalls;
            if (!ambDetalls) text.Visible = false;
            if (ambDetalls)
            {
                detalls.Location = new Point(marge - S(2), y);
                y = detalls.Bottom + S(8);
                if (text.Visible) { text.SetBounds(marge, y, dins, S(170)); y = text.Bottom + S(10); }
            }

            // Botons: el principal a la dreta
            string t1 = "Tancar", t2 = "";
            bool actiu2 = true;
            if (fase == Fase.Inici) t2 = "Instal·lar";
            else if (fase == Fase.Installant) { t1 = ""; t2 = "Instal·lant..."; actiu2 = false; }
            else if (fase == Fase.Acabat) t2 = "Obrir Arranjaments";
            else if (fase == Fase.Error) t2 = "Tornar-ho a provar";
            else if (fase == Fase.SenseCarpeta) t2 = "Triar la carpeta...";
            y += S(8);
            int altBoto = S(30), x = ample - marge;
            boto2.Text = t2; boto2.Enabled = actiu2;
            int a2 = Math.Max(S(96), TextRenderer.MeasureText(t2, Font).Width + S(28));
            boto2.SetBounds(x - a2, y, a2, altBoto); x -= a2 + S(8);
            boto1.Visible = t1 != "";
            if (t1 != "")
            {
                boto1.Text = t1;
                boto1.SetBounds(x - S(96), y, S(96), altBoto);
            }
            botoAjuda.Visible = fase == Fase.Error;
            if (botoAjuda.Visible) botoAjuda.SetBounds(marge, y, TextRenderer.MeasureText(botoAjuda.Text, Font).Width + S(28), altBoto);
            AcceptButton = actiu2 ? boto2 : null;
            y += altBoto + S(20);

            ClientSize = new Size(ample, y);
            ResumeLayout();
            llista.Invalidate();
        }

        void PintaLlista(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            int fila = S(42), d = S(20);
            for (int i = 0; i < passos.Count; i++)
            {
                Pas p = passos[i];
                int y = i * fila;
                Rectangle r = new Rectangle(S(2), y + (fila - S(8) - d) / 2, d, d);
                if (p.Estat == EstatPas.Pendent)
                {
                    using (Pen pen = new Pen(Color.FromArgb(190, 190, 190), 1.6f * f)) g.DrawEllipse(pen, r);
                }
                else if (p.Estat == EstatPas.EnMarxa)
                {
                    using (Pen fons = new Pen(Color.FromArgb(215, 225, 240), 2.4f * f)) g.DrawEllipse(fons, r);
                    using (Pen pen = new Pen(Color.FromArgb(0, 103, 192), 2.4f * f))
                    {
                        pen.StartCap = LineCap.Round; pen.EndCap = LineCap.Round;
                        g.DrawArc(pen, r, angle, 100);
                    }
                }
                else if (p.Estat == EstatPas.Fet)
                {
                    using (Brush b = new SolidBrush(Color.FromArgb(46, 160, 67))) g.FillEllipse(b, r);
                    using (Pen pen = new Pen(Color.White, 2f * f))
                    {
                        pen.StartCap = LineCap.Round; pen.EndCap = LineCap.Round; pen.LineJoin = LineJoin.Round;
                        g.DrawLines(pen, new PointF[] {
                            new PointF(r.X + d * 0.27f, r.Y + d * 0.52f), new PointF(r.X + d * 0.43f, r.Y + d * 0.68f), new PointF(r.X + d * 0.73f, r.Y + d * 0.34f) });
                    }
                }
                else
                {
                    using (Brush b = new SolidBrush(Color.FromArgb(218, 119, 24))) g.FillEllipse(b, r);
                    using (Pen pen = new Pen(Color.White, 2.2f * f))
                    {
                        pen.StartCap = LineCap.Round; pen.EndCap = LineCap.Round;
                        g.DrawLine(pen, r.X + d * 0.5f, r.Y + d * 0.24f, r.X + d * 0.5f, r.Y + d * 0.56f);
                        g.DrawLine(pen, r.X + d * 0.5f, r.Y + d * 0.76f, r.X + d * 0.5f, r.Y + d * 0.765f);
                    }
                }
                int x = S(34);
                TextFormatFlags tf = TextFormatFlags.NoPrefix | TextFormatFlags.NoPadding | TextFormatFlags.EndEllipsis;
                TextRenderer.DrawText(g, p.Titol, lletraTitolPas, new Rectangle(x, y, llista.Width - x, S(19)), SystemColors.WindowText, tf);
                TextRenderer.DrawText(g, p.Detall, lletraDetall, new Rectangle(x, y + S(18), llista.Width - x, S(18)), SystemColors.GrayText, tf);
            }
        }

        // ---------------------------------------------------------------- Lectura del que escriu l'instal·lador

        // Una línia del registre. Les que comencen per «@@» són avisos de progrés i no es mostren.
        void RepLinia(string linia)
        {
            if (linia == null) return;
            if (linia.StartsWith("@@"))
            {
                string[] parts = linia.Substring(2).Split(new char[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length >= 3 && parts[0] == "PAS") Marca(parts[1], parts[2]);
                else if (parts.Length >= 2 && parts[0] == "FI") finalRebut = parts[1] == "ok";
                return;
            }
            registre.Append(linia).Append("\r\n");
            text.AppendText(linia + "\r\n");
            string neta = linia.Trim();
            if (neta.StartsWith("[fet]")) neta = neta.Substring(5).Trim();
            else if (neta.StartsWith("[falta]")) neta = neta.Substring(7).Trim();
            if (neta != "" && !neta.StartsWith("==")) estat.Text = neta;
        }

        void Marca(string id, string estatText)
        {
            EstatPas nou = estatText == "inici" ? EstatPas.EnMarxa : (estatText == "ok" ? EstatPas.Fet : EstatPas.Falla);
            if (id == "final") comprovacio = nou;
            else foreach (Pas p in passos) if (p.Id == id) p.Estat = nou;
            // la barra: cada pas (i la comprovació final) val una part; el que està en marxa, mitja
            double fets = Valor(comprovacio);
            foreach (Pas p in passos) fets += Valor(p.Estat);
            barra.Value = (int)(1000 * fets / (passos.Count + 1));
            llista.Invalidate();
            if (id == "musescore" && nou == EstatPas.EnMarxa && !avisatAMitges && opcions.Captura != null)
            {
                avisatAMitges = true;
                llista.Update();
                Captura(opcions.Captura.Replace(".png", "-mig.png"));
            }
        }

        static double Valor(EstatPas e) { return e == EstatPas.Fet || e == EstatPas.Falla ? 1 : (e == EstatPas.EnMarxa ? 0.5 : 0); }

        // ---------------------------------------------------------------- Instal·lació

        void Comenca()
        {
            if (fase == Fase.Installant) return;
            foreach (Pas p in passos) p.Estat = EstatPas.Pendent;
            comprovacio = EstatPas.Pendent; finalRebut = null; missatgeError = "";
            registre.Length = 0; text.Clear(); barra.Value = 0; estat.Text = "Començant...";
            fase = Fase.Installant;
            Colloca();
            rellotge.Start();
            if (opcions.Prova) { Simula(); return; }

            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe");
                string guio = Path.Combine(Path.Combine(carpeta, "instalacio"), "instalar-windows.ps1");
                psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + guio + "\" -SensePreguntes";
                psi.WorkingDirectory = carpeta;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                psi.RedirectStandardInput = true;
                psi.StandardOutputEncoding = new UTF8Encoding(false);
                psi.StandardErrorEncoding = new UTF8Encoding(false);
                psi.EnvironmentVariables["ARRANJAMENTS_PROGRES"] = "1";
                // si ens han obert des d'un PowerShell més nou, la seua llista de mòduls trencaria el Windows PowerShell fill
                psi.EnvironmentVariables.Remove("PSModulePath");
                Process p = new Process();
                p.StartInfo = psi;
                p.OutputDataReceived += delegate(object s, DataReceivedEventArgs e) { Envia(e.Data); };
                p.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e) { Envia(e.Data); };
                p.Start();
                proces = p;
                p.StandardInput.Close();
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();
                Thread fil = new Thread(delegate()
                {
                    // sense esperar que es tanquen les canonades: un programa instal·lat podria deixar-les obertes
                    while (!p.WaitForExit(500)) { }
                    int codi = p.ExitCode;
                    Thread.Sleep(600);
                    try { BeginInvoke(new Action(delegate { Acaba(codi); })); } catch { }
                });
                fil.IsBackground = true;
                fil.Start();
            }
            catch (Exception ex)
            {
                RepLinia("No s'ha pogut engegar l'instal·lador: " + ex.Message);
                Acaba(1);
            }
        }

        void Envia(string linia)
        {
            if (linia == null) return;
            try { BeginInvoke(new Action(delegate { RepLinia(linia); })); } catch { }
        }

        void Acaba(int codi)
        {
            if (fase != Fase.Installant) return;
            proces = null;
            rellotge.Stop();
            bool be = codi == 0 && finalRebut == true;
            List<string> fallats = new List<string>();
            foreach (Pas p in passos)
            {
                if (p.Estat == EstatPas.EnMarxa) p.Estat = EstatPas.Falla;
                if (p.Estat != EstatPas.Fet) be = false;
                if (p.Estat == EstatPas.Falla) fallats.Add(p.Titol);
            }
            if (be) { barra.Value = 1000; fase = Fase.Acabat; }
            else
            {
                if (fallats.Count > 0) missatgeError = "Ha faltat: " + string.Join(", ", fallats.ToArray()) + ".";
                else if (finalRebut == null) missatgeError = "L'instal·lador s'ha aturat abans d'acabar.";
                else missatgeError = "La comprovació final ha trobat algun problema.";
                fase = Fase.Error;
            }
            CodiEixida = be ? 0 : 1;
            Colloca();
            if (opcions.Registre != null)
            {
                try { File.WriteAllText(opcions.Registre, registre.ToString() + "RESULTAT: " + (be ? "tot a punt" : missatgeError) + "\r\n", new UTF8Encoding(false)); } catch { }
            }
            if (opcions.Captura != null) { Refresh(); Captura(opcions.Captura); }
            if (opcions.Auto) Close();
        }

        // Mode de prova: les mateixes línies que escriuria l'instal·lador, però sense instal·lar res.
        void Simula()
        {
            List<string> linies = new List<string>();
            int n = 0;
            foreach (Pas p in passos)
            {
                n++;
                bool falla = opcions.ProvaError && p.Id == "musescore";
                linies.Add("@@PAS " + p.Id + " inici");
                linies.Add("");
                linies.Add("== " + n + ". " + p.Titol + " (prova) ==");
                linies.Add(falla ? "  [falta]  No he pogut instal·lar " + p.Titol + " automàticament (prova)." : "  [fet]    " + p.Titol + " (prova, no s'ha instal·lat res)");
                linies.Add("@@PAS " + p.Id + (falla ? " falla" : " ok"));
            }
            linies.Add("@@PAS final inici");
            linies.Add("== Comprovació final (prova) ==");
            linies.Add("@@PAS final " + (opcions.ProvaError ? "falla" : "ok"));
            linies.Add("@@FI " + (opcions.ProvaError ? "falla 1" : "ok"));
            int k = 0;
            System.Windows.Forms.Timer t = new System.Windows.Forms.Timer();
            t.Interval = 250;
            t.Tick += delegate
            {
                if (k < linies.Count) { RepLinia(linies[k]); k++; }
                else { t.Stop(); t.Dispose(); Acaba(opcions.ProvaError ? 1 : 0); }
            };
            t.Start();
        }

        // ---------------------------------------------------------------- Accions

        void Boto1() { Close(); }

        void Boto2()
        {
            if (fase == Fase.Inici || fase == Fase.Error)
            {
                Comenca();
            }
            else if (fase == Fase.Acabat)
            {
                if (!opcions.Prova) Obri(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "Arranjaments.lnk"));
                Close();
            }
            else if (fase == Fase.SenseCarpeta)
            {
                using (FolderBrowserDialog tria = new FolderBrowserDialog())
                {
                    tria.Description = "Tria la carpeta d'Arranjaments (on veus el fitxer README.md).";
                    tria.ShowNewFolderButton = false;
                    if (tria.ShowDialog(this) != DialogResult.OK) return;
                    if (TeInstalador(tria.SelectedPath)) { carpeta = tria.SelectedPath; fase = Fase.Inici; Colloca(); }
                    else MessageBox.Show(this, "Esta no és la carpeta d'Arranjaments. La carpeta bona és aquella on veus el fitxer README.md i la carpeta «instalacio».",
                        "Instal·lar Arranjaments", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
            }
        }

        static void Obri(string que)
        {
            try { Process.Start(que); } catch { }
        }

        void AlTancar(object sender, FormClosingEventArgs e)
        {
            if (fase != Fase.Installant || opcions.Prova) return;
            DialogResult r = MessageBox.Show(this,
                "La instal·lació encara no ha acabat. Si ixes ara, quedarà a mitges. Podràs tornar a obrir l'instal·lador més avant: només fa el que falta.\n\nVols eixir?",
                "Instal·lar Arranjaments", MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2);
            if (r != DialogResult.Yes) { e.Cancel = true; return; }
            CodiEixida = 1;
            try
            {
                if (proces != null && !proces.HasExited)
                {
                    // atura també els programes que haja engegat l'instal·lador
                    ProcessStartInfo mata = new ProcessStartInfo("taskkill.exe", "/PID " + proces.Id + " /T /F");
                    mata.CreateNoWindow = true; mata.UseShellExecute = false;
                    Process.Start(mata);
                }
            }
            catch { }
        }

        void Captura(string ruta)
        {
            try
            {
                using (Bitmap b = new Bitmap(Width, Height))
                {
                    DrawToBitmap(b, new Rectangle(0, 0, Width, Height));
                    b.Save(ruta, ImageFormat.Png);
                }
            }
            catch { }
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            if (!opcions.Auto) return;
            if (fase == Fase.SenseCarpeta) { CodiEixida = 2; Close(); return; }
            Comenca();
        }
    }

    static class Programa
    {
        [STAThread]
        static int Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Finestra finestra = new Finestra(new Opcions(args));
            Application.Run(finestra);
            return finestra.CodiEixida;
        }
    }
}
