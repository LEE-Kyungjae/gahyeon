using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Windows.Forms;

// Native Windows surfaces using the same dimensions and icon order as the Mac overlay.
class GlassPanel : Form {
    public int CornerRadius = 16;
    public bool AcceptsFocus;
    public bool ConversationLines;
    protected override bool ShowWithoutActivation { get { return !AcceptsFocus; } }
    protected override CreateParams CreateParams { get { var p=base.CreateParams; p.ExStyle|=0x80; return p; } }
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr hwnd,int attribute,ref int value,int size);
    public GlassPanel() { DoubleBuffered=true; AutoScaleMode=AutoScaleMode.None; }
    public static GraphicsPath Rounded(RectangleF r,float radius) {
        var p=new GraphicsPath();float d=radius*2;
        p.AddArc(r.X,r.Y,d,d,180,90);p.AddArc(r.Right-d,r.Y,d,d,270,90);
        p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90);p.AddArc(r.X,r.Bottom-d,d,d,90,90);p.CloseFigure();return p;
    }
    protected override void OnHandleCreated(EventArgs e) {
        base.OnHandleCreated(e);
        try { int dark=1,round=2;DwmSetWindowAttribute(Handle,20,ref dark,4);DwmSetWindowAttribute(Handle,33,ref round,4); } catch(DllNotFoundException) {}
    }
    protected override void OnSizeChanged(EventArgs e) {
        base.OnSizeChanged(e);if(Width<2||Height<2)return;
        using(var p=Rounded(new RectangleF(0,0,Width,Height),CornerRadius)) { var old=Region;Region=new Region(p);if(old!=null)old.Dispose(); }
    }
    protected override void OnPaint(PaintEventArgs e) {
        base.OnPaint(e);e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var p=Rounded(new RectangleF(.5f,.5f,Width-1,Height-1),CornerRadius))
        using(var fill=new SolidBrush(Color.FromArgb(36,40,48)))
        using(var edge=new Pen(Color.FromArgb(64,68,76))) {e.Graphics.FillPath(fill,p);e.Graphics.DrawPath(edge,p);if(ConversationLines){e.Graphics.DrawLine(edge,16,48,Width-16,48);e.Graphics.DrawLine(edge,16,Height-100,Width-16,Height-100);}}
    }
}

class IconButton : Button {
    public string Symbol;
    bool hover;
    public IconButton(string symbol) {
        Symbol=symbol;Size=new Size(30,30);FlatStyle=FlatStyle.Flat;FlatAppearance.BorderSize=0;
        SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer,true);
        Text="";Cursor=Cursors.Hand;TabStop=true;
    }
    protected override void OnMouseEnter(EventArgs e){hover=true;Invalidate();base.OnMouseEnter(e);}
    protected override void OnMouseLeave(EventArgs e){hover=false;Invalidate();base.OnMouseLeave(e);}
    protected override void OnPaint(PaintEventArgs e) {
        var g=e.Graphics;g.Clear(BackColor);g.SmoothingMode=SmoothingMode.AntiAlias;
        using(var path=GlassPanel.Rounded(new RectangleF(.5f,.5f,Width-1,Height-1),7))
        using(var fill=new SolidBrush(hover?Color.FromArgb(64,68,76):BackColor))
        using(var border=new Pen(Focused?Color.FromArgb(131,216,219):BackColor)) {g.FillPath(fill,path);g.DrawPath(border,path);}
        g.TranslateTransform((Width-30)/2f,(Height-30)/2f);
        using(var p=new Pen(Enabled?ForeColor:Color.Gray,1.5f)) {
            p.StartCap=p.EndCap=LineCap.Round;p.LineJoin=LineJoin.Round;
            switch(Symbol) {
                case "close":g.DrawLine(p,10,10,20,20);g.DrawLine(p,20,10,10,20);break;
                case "more":g.DrawEllipse(p,7,14,2,2);g.DrawEllipse(p,14,14,2,2);g.DrawEllipse(p,21,14,2,2);break;
                case "stop":g.DrawEllipse(p,7,7,16,16);g.DrawRectangle(p,12,12,6,6);break;
                case "react":g.DrawPolygon(p,new[]{new Point(15,5),new Point(18,12),new Point(25,15),new Point(18,18),new Point(15,25),new Point(12,18),new Point(5,15),new Point(12,12)});break;
                case "character":g.DrawEllipse(p,7,7,16,16);g.DrawEllipse(p,12,10,6,6);g.DrawArc(p,9,17,12,10,205,130);break;
                case "refresh":g.DrawArc(p,8,8,14,14,40,285);g.DrawLines(p,new[]{new Point(22,7),new Point(22,12),new Point(17,12)});break;
                case "reset":g.DrawEllipse(p,9,9,12,12);g.DrawLine(p,15,6,15,11);g.DrawLine(p,15,19,15,24);g.DrawLine(p,6,15,11,15);g.DrawLine(p,19,15,24,15);break;
                case "pause":g.DrawLine(p,12,9,12,21);g.DrawLine(p,18,9,18,21);break;
                case "play":g.DrawPolygon(p,new[]{new Point(11,8),new Point(22,15),new Point(11,22)});break;
                case "pin":g.DrawLines(p,new[]{new Point(11,8),new Point(19,8),new Point(18,15),new Point(21,18),new Point(9,18),new Point(12,15),new Point(11,8)});g.DrawLine(p,15,18,15,24);break;
                case "power":g.DrawArc(p,8,8,14,14,-55,290);g.DrawLine(p,15,6,15,14);break;
                case "chat":using(var path=GlassPanel.Rounded(new RectangleF(7,8,16,12),3))g.DrawPath(p,path);g.DrawLines(p,new[]{new Point(10,20),new Point(9,24),new Point(15,20)});break;
                case "mic-off":case "mic":using(var path=GlassPanel.Rounded(new RectangleF(12,6,6,13),3))g.DrawPath(p,path);g.DrawArc(p,9,12,12,10,0,180);g.DrawLine(p,15,22,15,25);if(Symbol=="mic-off")g.DrawLine(p,6,6,24,24);break;
                case "sound":g.DrawPolygon(p,new[]{new Point(7,12),new Point(11,12),new Point(16,8),new Point(16,22),new Point(11,18),new Point(7,18)});if(Text=="×")g.DrawLine(p,7,7,23,23);else{g.DrawArc(p,15,10,7,10,-70,140);g.DrawArc(p,15,7,12,16,-65,130);}break;
                case "send":g.DrawLine(p,15,22,15,8);g.DrawLines(p,new[]{new Point(10,13),new Point(15,8),new Point(20,13)});break;
                case "up":g.DrawLines(p,new[]{new Point(10,17),new Point(15,12),new Point(20,17)});break;
                case "down":g.DrawLines(p,new[]{new Point(10,12),new Point(15,17),new Point(20,12)});break;
            }
        }
    }
}
