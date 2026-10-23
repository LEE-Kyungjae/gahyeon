using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Web.Script.Serialization;
using System.Windows.Forms;

static class ConversationDesign {
    public static string PathFor(string relative) {
        string path=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..",relative);
        return File.Exists(path)?path:Path.Combine(Environment.CurrentDirectory,relative);
    }
    static Dictionary<string,object> values=Load();
    static Dictionary<string,object> Load(){string p=PathFor("config/desktop-conversation-design.json");return File.Exists(p)?new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(p)):new Dictionary<string,object>();}
    public static int Number(string name,int fallback){return values.ContainsKey(name)?Convert.ToInt32(values[name]):fallback;}
    public static readonly Color Surface=Color.FromArgb(36,40,48),Accent=Color.FromArgb(131,216,219),Muted=Color.FromArgb(167,175,186);
}
sealed class RosterCard : Button {
    public uint ModelIndex;
    public bool Selected;
    public LetteringArtwork Lettering;
    public Image Preview;
    public RectangleF Source;
    bool hover;
    public RosterCard(){FlatStyle=FlatStyle.Flat;FlatAppearance.BorderSize=0;Text="";TabStop=true;Cursor=Cursors.Hand;SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer,true);}
    protected override void OnMouseEnter(EventArgs e){hover=true;Invalidate();base.OnMouseEnter(e);}
    protected override void OnMouseLeave(EventArgs e){hover=false;Invalidate();base.OnMouseLeave(e);}
    protected override void OnPaint(PaintEventArgs e){
        var g=e.Graphics;g.Clear(BackColor);g.SmoothingMode=SmoothingMode.AntiAlias;g.InterpolationMode=InterpolationMode.HighQualityBicubic;
        using(var shape=GlassPanel.Rounded(new RectangleF(1,1,Width-2,Height-2),12))
        using(var fill=new SolidBrush(hover?Color.FromArgb(58,62,70):Color.FromArgb(44,48,56)))
        using(var pen=new Pen(Selected||Focused?ConversationDesign.Accent:Color.FromArgb(65,69,77),Selected||Focused?2:1)){g.FillPath(fill,shape);g.DrawPath(pen,shape);}
        if(Preview!=null&&Source.Width>0){float f=Math.Min(124/Source.Width,74/Source.Height);var size=new SizeF(Source.Width*f,Source.Height*f);g.DrawImage(Preview,new RectangleF((Width-size.Width)/2,8,size.Width,size.Height),Source,GraphicsUnit.Pixel);}
        if(Lettering!=null){float f=Math.Min((Width-28)/Lettering.Bounds.Width,27/Lettering.Bounds.Height);var size=new SizeF(Lettering.Bounds.Width*f,Lettering.Bounds.Height*f);g.DrawImage(Lettering.Image,new RectangleF((Width-size.Width)/2,Height-32+(27-size.Height)/2,size.Width,size.Height),Lettering.Bounds,GraphicsUnit.Pixel);}
        if(Selected)TextRenderer.DrawText(g,"✓",new Font("Segoe UI",10),new Point(10,8),ConversationDesign.Accent);
    }
    protected override void Dispose(bool disposing){if(disposing){if(Preview!=null)Preview.Dispose();if(Lettering!=null)Lettering.Dispose();}base.Dispose(disposing);}
}
sealed class RosterPicker : GlassPanel {
    public readonly List<RosterCard> Cards=new List<RosterCard>();
    public CheckBox Variant;
    public RosterPicker(uint current,Action<uint> select){
        AcceptsFocus=true;Text="캐릭터 선택";FormBorderStyle=FormBorderStyle.None;ShowInTaskbar=false;StartPosition=FormStartPosition.Manual;
        ClientSize=new Size(ConversationDesign.Number("pickerWidth",340),ConversationDesign.Number("pickerHeight",556));BackColor=ConversationDesign.Surface;ForeColor=Color.White;KeyPreview=true;
        KeyDown+=(s,e)=>{if(e.KeyCode==Keys.Escape)Close();};
        var title=new Label{Text="캐릭터 선택",Location=new Point(16,12),Size=new Size(180,22),Font=new Font("Segoe UI",10,FontStyle.Bold),BackColor=BackColor,ForeColor=Color.White};Controls.Add(title);
        var close=new IconButton("close"){AccessibleName="닫기",Location=new Point(Width-42,8),ForeColor=Color.White,BackColor=BackColor};close.Click+=(s,e)=>Close();Controls.Add(close);
        string[] ids={"gahyeon","zeze","rogue","pirate","fighter","fighter-unmasked","child","hacker"}, labels={"가현","재재","도적","해적","격투가","격투가 (가면 없음)","아이","해커"};
        var manifest=(Dictionary<string,object>)new JavaScriptSerializer().DeserializeObject(File.ReadAllText(ConversationDesign.PathFor("assets/character-previews/v001/manifest.json")));
        var indices=new[]{0,1,2,3,4,6,7};
        for(int slot=0;slot<indices.Length;slot++){
            int index=indices[slot],assetIndex=index==4&&current==5?5:index;
            var card=new RosterCard{ModelIndex=(uint)assetIndex,Selected=current==index||(index==4&&current==5),AccessibleName=labels[index],Location=new Point(10+slot%2*164,44+slot/2*124),Size=new Size(156,116),BackColor=BackColor,ForeColor=Color.White,Lettering=LetteringArtwork.Load(ids[index])};
            foreach(Dictionary<string,object> asset in (object[])manifest["assets"]){if((string)asset["id"]!=ids[assetIndex])continue;var b=(object[])asset["alphaBounds"];float l=Convert.ToSingle(b[0]),t=Convert.ToSingle(b[1]),r=Convert.ToSingle(b[2]),bottom=Convert.ToSingle(b[3]);card.Source=new RectangleF(l,t,r-l,(bottom-t)*.58f);card.Preview=Image.FromFile(ConversationDesign.PathFor((string)asset["path"]));}
            card.Click+=(s,e)=>{uint model=((RosterCard)s).ModelIndex;Close();select(model);};Cards.Add(card);Controls.Add(card);
        }
        if(current==4||current==5){Variant=new CheckBox{Text="가면 없음",Checked=current==5,Location=new Point(16,Height-32),Size=new Size(140,24),BackColor=BackColor,ForeColor=Color.White};Variant.CheckedChanged+=(s,e)=>{uint model=Variant.Checked?5u:4u;Close();select(model);};Controls.Add(Variant);}
    }
}
