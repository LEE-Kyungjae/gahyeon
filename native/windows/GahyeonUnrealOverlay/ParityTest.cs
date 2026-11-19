using System;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

class OverlayParityTest {
    static object Field(object o,string n){return o.GetType().GetField(n,BindingFlags.NonPublic|BindingFlags.Instance).GetValue(o);}
    static void Call(object o,string n){o.GetType().GetMethod(n,BindingFlags.NonPublic|BindingFlags.Instance).Invoke(o,null);}
    static void Check(bool ok,string message){if(!ok)throw new Exception(message);Console.WriteLine("PASS "+message);}
    static void Pump(int milliseconds){var end=DateTime.UtcNow.AddMilliseconds(milliseconds);while(DateTime.UtcNow<end){Application.DoEvents();Thread.Sleep(10);}}
    static void WaitFrame(object app,long previous) {
        var deadline=DateTime.UtcNow.AddSeconds(5);
        while((long)Field(app,"sequence")==previous&&DateTime.UtcNow<deadline){Thread.Sleep(40);Call(app,"Frame");}
    }
    [STAThread] static int Main(string[] args) {
        try {
            Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
            using(var app=new GahyeonOverlay()) {
                app.Show();Pump(300);Call(app,"Frame");
                var chat=(Form)Field(app,"chat");var bubble=(Form)Field(app,"bubble");var controls=(Form)Field(app,"controls");
                Check(chat.Visible&&!bubble.Visible&&!controls.Visible,"conversation is the only visible control surface");
                Check(chat.ClientSize==new Size(360,280),"shared default conversation dimensions");
                Check(((Control)Field(app,"mic")).Parent==chat&&((Control)Field(app,"sound")).Parent==chat,"voice controls belong to conversation");
                ((Button)Field(app,"closeChatButton")).PerformClick();Check(!chat.Visible&&bubble.Visible&&app.Visible,"close chat preserves character and reveals reopen control");
                ((Button)bubble.Controls[0]).PerformClick();Check(chat.Visible&&!bubble.Visible,"reopen chat restores one surface");
                ((Button)Field(app,"expand")).PerformClick();Check(chat.Height==440,"history expands upwards");
                var area=Screen.FromControl(app).WorkingArea;
                foreach(var location in new[]{new Point(area.Left,area.Top),new Point(area.Right-app.Width,area.Top),new Point(area.Right-app.Width,area.Bottom-app.Height)}){
                    app.Location=location;Call(app,"LayoutPanels");Check(area.Contains(chat.Bounds),"conversation within work area");var stable=app.Bounds;Call(app,"LayoutPanels");Check(app.Bounds==stable,"layout never moves character at screen edge");
                }
                ((Button)Field(app,"expand")).PerformClick();Check(chat.Height==280,"history returns to compact conversation");
                Call(app,"Frame");
                var beforeZoom=app.Bounds;var shape=(RectangleF)Field(app,"bodyBounds");var anchor=new PointF(app.Left+app.Width*(shape.X+shape.Width/2),app.Top+app.Height*(shape.Y+shape.Height/2));
                app.GetType().GetMethod("ChangeScale",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(app,new object[]{.1f});Pump(150);Call(app,"Frame");
                shape=(RectangleF)Field(app,"bodyBounds");var bodyRect=new RectangleF(app.Left+app.Width*shape.X,app.Top+app.Height*shape.Y,app.Width*shape.Width,app.Height*shape.Height);Check(!bodyRect.IntersectsWith(chat.Bounds)&&area.Contains(chat.Bounds),"responsive zoom keeps chat visible and clear");Check(Math.Abs(app.Top+app.Height*(shape.Y+shape.Height/2)-anchor.Y)<2,"responsive zoom preserves vertical center");
                chat.Hide();var hiddenAnchor=new PointF(app.Left+app.Width*(shape.X+shape.Width/2),app.Top+app.Height*(shape.Y+shape.Height/2));
                app.GetType().GetMethod("ChangeScale",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(app,new object[]{-.1f});Pump(150);
                Check(Math.Abs(app.Left+app.Width*(shape.X+shape.Width/2)-hiddenAnchor.X)<2&&Math.Abs(app.Top+app.Height*(shape.Y+shape.Height/2)-hiddenAnchor.Y)<2,"hidden chat preserves center zoom");chat.Show();Call(app,"LayoutPanels");
                var rightEvent=new MouseEventArgs(MouseButtons.Right,1,100,100,0);app.GetType().GetMethod("OnMouseDown",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(app,new object[]{rightEvent});
                app.GetType().GetMethod("OnMouseMove",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(app,new object[]{new MouseEventArgs(MouseButtons.Right,0,120,100,0)});
                Check((float)Field(app,"yaw")<0,"right drag follows corrected rotation direction");
                Call(app,"TogglePin");Check(!app.TopMost&&!chat.TopMost,"pin applies to conversation group");Call(app,"TogglePin");
                Check(!(bool)Field(app,"soundOn"),"speaker defaults off");Check(((IconButton)Field(app,"mic")).Symbol=="mic-off","microphone defaults to off glyph");((Button)Field(app,"sound")).PerformClick();Check((bool)Field(app,"soundOn"),"speaker on action connected");((Button)Field(app,"sound")).PerformClick();Check(!(bool)Field(app,"soundOn"),"speaker off action connected");
                long before=(long)Field(app,"sequence");WaitFrame(app,before);Check((long)Field(app,"sequence")!=before,"live Unreal frames");
                Call(app,"TogglePause");before=(long)Field(app,"sequence");Pump(150);Call(app,"Frame");Check((long)Field(app,"sequence")==before,"pause freezes visible frames");Call(app,"TogglePause");WaitFrame(app,before);Check((long)Field(app,"sequence")!=before,"resume restores frames");
                Call(app,"ResetPlacement");Check((float)Field(app,"scale")==1&&(float)Field(app,"yaw")==0,"reset restores scale and rotation");
                ((Button)Field(app,"characterButton")).PerformClick();Pump(150);var picker=(RosterPicker)Field(app,"picker");
                Check(picker!=null,"picker opens: "+((RichTextBox)Field(app,"history")).Text);
                Check(picker.Visible&&picker.Cards.Count==7,"seven identity cards instead of duplicate variant row");
                Check(picker.Size==new Size(340,556)&&area.Contains(picker.Bounds),"shared picker size stays on screen");
                string[] names={"가현","재재","도적","해적","격투가","아이","해커"};
                for(int i=0;i<7;i++){var card=picker.Cards[i];Check(card.AccessibleName==names[i]&&card.Preview!=null&&card.Lettering!=null,"preview and name "+names[i]);Check(card.Left==10+i%2*164&&card.Top==44+i/2*124,"two column card "+i);}
                picker.Close();uint chosen=99;
                using(var variant=new RosterPicker(4,n=>chosen=n)){variant.Show();variant.Variant.Checked=true;Check(chosen==5,"unmasked variant selected within fighter");}
                using(var variant=new RosterPicker(5,n=>chosen=n)){variant.Show();variant.Variant.Checked=false;Check(chosen==4,"masked variant restored within fighter");}
                ((Button)Field(app,"reactButton")).PerformClick();Pump(350);bool systemMotion=true;var motionArgs=new object[]{(uint)0x1042,(uint)0,systemMotion,(uint)0};app.GetType().GetMethod("SystemParametersInfo",BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,motionArgs);systemMotion=(bool)motionArgs[2];
                Check(systemMotion?Math.Abs((float)Field(app,"reactionYaw"))>.2:Math.Abs((float)Field(app,"reactionYaw"))<.2,systemMotion?"reaction changes actual Unreal yaw":"Windows reduced animation setting respected");Pump(2400);Check(Math.Abs((float)Field(app,"reactionYaw"))<.2,"reaction returns to neutral yaw");
                app.GetType().GetField("reducedMotion",BindingFlags.NonPublic|BindingFlags.Instance).SetValue(app,true);Call(app,"React");Pump(300);Check(Math.Abs((float)Field(app,"reactionYaw"))<.2,"reduced motion suppresses reactions");
                if(args.Length>0){Directory.CreateDirectory(args[0]);using(var bmp=new Bitmap(chat.Width,chat.Height)){chat.DrawToBitmap(bmp,chat.ClientRectangle);bmp.Save(Path.Combine(args[0],"conversation.png"));}}
                app.Close();
            }
            return 0;
        }catch(Exception error){Console.WriteLine(error);return 1;}
    }
}
