using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Web.Script.Serialization;
using System.Windows.Forms;

sealed class LetteringArtwork : IDisposable {
    public Image Image;
    public RectangleF Bounds;
    public static LetteringArtwork Load(string id) {
        string manifest=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..","assets","character-lettering","v001","manifest.json");
        if(!File.Exists(manifest))manifest=Path.Combine(Environment.CurrentDirectory,"assets","character-lettering","v001","manifest.json");
        if(!File.Exists(manifest))return null;
        var root=(Dictionary<string,object>)new JavaScriptSerializer().DeserializeObject(File.ReadAllText(manifest));
        foreach(Dictionary<string,object> asset in (object[])root["assets"]) {
            if((string)asset["id"]!=id)continue;
            string path=Path.Combine(Path.GetDirectoryName(manifest),id+".png");
            if(!File.Exists(path))return null;
            var b=(object[])asset["alphaBounds"];
            return new LetteringArtwork {Image=Image.FromFile(path),Bounds=RectangleF.FromLTRB(Convert.ToSingle(b[0]),Convert.ToSingle(b[1]),Convert.ToSingle(b[2]),Convert.ToSingle(b[3]))};
        }
        return null;
    }
    public void Dispose(){Image.Dispose();}
}

sealed class LetteringMenuRenderer : ToolStripProfessionalRenderer {
    protected override void OnRenderToolStripBackground(ToolStripRenderEventArgs e){e.Graphics.Clear(Color.FromArgb(29,35,44));}
    protected override void OnRenderMenuItemBackground(ToolStripItemRenderEventArgs e){
        if(e.Item.Selected)using(var brush=new SolidBrush(Color.FromArgb(57,78,101)))e.Graphics.FillRectangle(brush,new Rectangle(Point.Empty,e.Item.Size));
    }
    protected override void OnRenderItemCheck(ToolStripItemImageRenderEventArgs e){
        using(var pen=new Pen(Color.Cyan,2))e.Graphics.DrawLines(pen,new[]{new Point(8,28),new Point(12,32),new Point(20,22)});
    }
    protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e){
        var art=e.Item.Tag as LetteringArtwork;
        if(art==null){e.TextColor=Color.White;base.OnRenderItemText(e);return;}
        float factor=Math.Min(136/art.Bounds.Width,40/art.Bounds.Height);
        var size=new SizeF(art.Bounds.Width*factor,art.Bounds.Height*factor);
        e.Graphics.InterpolationMode=System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
        e.Graphics.DrawImage(art.Image,new RectangleF(32+(144-size.Width)/2,(56-size.Height)/2,size.Width,size.Height),art.Bounds,GraphicsUnit.Pixel);
        if(e.Item.Text.Contains("(가면 없음)"))TextRenderer.DrawText(e.Graphics,"(가면 없음)",e.TextFont,new Rectangle(176,8,104,40),Color.White,TextFormatFlags.VerticalCenter|TextFormatFlags.SingleLine);
    }
}
