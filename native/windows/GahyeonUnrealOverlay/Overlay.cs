using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Media;

class GahyeonOverlay : Form {
    const string Frames = "{36CB1D68-2643-421D-85B1-61FCCFDA0401}";
    MemoryMappedFile memory;
    MemoryMappedViewAccessor view;
    long sequence;
    Timer timer = new Timer { Interval = 33 };
    GlassPanel controls = new GlassPanel(), bubble = new GlassPanel { CornerRadius=18 }, chat = new GlassPanel { AcceptsFocus=true };
    ToolTip tips = new ToolTip();
    NotifyIcon tray;
    RosterPicker picker;
    Label activity=new Label();
    Button characterButton,moreButton,closeChatButton,reactButton;
    DateTime reactionStarted=DateTime.MinValue,nextIdleReaction=DateTime.UtcNow.AddSeconds(45),speakingUntil=DateTime.MinValue;
    float reactionYaw=Single.NaN,lastBaseYaw=Single.NaN;
    bool reducedMotion;
    [DllImport("user32.dll")] static extern bool SystemParametersInfo(uint action,uint parameter,out bool value,uint flags);
    IconButton controlsToggle, pauseButton, pinButton;
    bool paused, dragLocked, layoutBusy, characterHidden, rotatedDrag;
    float scale=1, yaw;
    Rectangle crop;
    RectangleF bodyBounds = new RectangleF(0,0,1,1);
    float bodySide=1;
    PointF? zoomCenter;
    bool zoomChatOnRight;
    uint appliedModel=UInt32.MaxValue;
    int contentHeight=640;
    RichTextBox history = new RichTextBox();
    TextBox input = new TextBox();
    Button mic, sound, expand;
    bool expanded, soundOn = false, recording, busy, pinned = true;
    Point drag, dragPointer, dragOrigin;
    bool pointerDragging;
    Timer recoveryTimer=new Timer {Interval=16};
    Point recoveryStart,recoveryTarget;
    DateTime recoveryBegan;
    Size panelLayoutSize;
    HttpClient http = new HttpClient { Timeout = TimeSpan.FromSeconds(60) };
    JavaScriptSerializer json = new JavaScriptSerializer();
    string installation = "windows-" + Environment.UserName;
    string session = "windows-" + Guid.NewGuid().ToString("N");
    string core = Environment.GetEnvironmentVariable("GAHYEON_CORE_URL") ?? "http://127.0.0.1:18080/api";
    SoundPlayer player;
    MemoryStream playing;
    Timer recordingLimit = new Timer { Interval = 30000 };
    [DllImport("winmm.dll", CharSet=CharSet.Unicode)] static extern int mciSendString(string command, StringBuilder result, int size, IntPtr callback);
    [DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr h);
    [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr h, IntPtr dc);
    [DllImport("gdi32.dll")] static extern IntPtr CreateCompatibleDC(IntPtr dc);
    [DllImport("gdi32.dll")] static extern IntPtr SelectObject(IntPtr dc, IntPtr obj);
    [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr obj);
    [DllImport("gdi32.dll")] static extern bool DeleteDC(IntPtr dc);
    [StructLayout(LayoutKind.Sequential)] struct Blend { public byte Op,Flags,Alpha,Format; }
    [DllImport("user32.dll", SetLastError=true)] static extern bool UpdateLayeredWindow(IntPtr h, IntPtr dst, ref Point pos, ref Size size, IntPtr src, ref Point origin, int key, ref Blend blend, int flags);
    protected override CreateParams CreateParams { get { var p=base.CreateParams; p.ExStyle |= 0x80000 | 0x80; return p; } }
    static void Prepare(Form f) { f.AutoScaleMode=AutoScaleMode.None; f.StartPosition=FormStartPosition.Manual; f.FormBorderStyle=FormBorderStyle.None; f.ShowInTaskbar=false; f.TopMost=true; f.BackColor=Color.FromArgb(35,39,47); f.ForeColor=Color.White; }
    Button Button(string symbol, string label, EventHandler action) {
        var b=new IconButton(symbol) { ForeColor=Color.White, BackColor=ConversationDesign.Surface, AccessibleName=label };
        tips.SetToolTip(b,label); b.Click+=action; return b;
    }
    public GahyeonOverlay() {
        Text="가현"; Prepare(this); Size=new Size(520,640); Location=new Point(500,120);
        string token=Environment.GetEnvironmentVariable("GAHYEON_CLIENT_TOKEN");
        if(!String.IsNullOrWhiteSpace(token)) http.DefaultRequestHeaders.Authorization=new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer",token);
        Prepare(controls);controls.ClientSize=new Size(1,1);
        Prepare(bubble);bubble.Text="채팅 열기";bubble.ClientSize=new Size(36,36);
        controlsToggle=(IconButton)Button("chat","채팅 열기",(s,e)=>ToggleChat());controlsToggle.Location=new Point(3,3);bubble.Controls.Add(controlsToggle);
        pauseButton=(IconButton)Button("pause","애니메이션 화면 일시정지",(s,e)=>TogglePause());
        pinButton=(IconButton)Button("pin","항상 위에 표시",(s,e)=>TogglePin());
        Prepare(chat);chat.Text="가현 채팅";chat.ClientSize=new Size(360,280);chat.BackColor=ConversationDesign.Surface;chat.ConversationLines=true;
        characterButton=Button("character","캐릭터 선택",(s,e)=>ShowCharacters());characterButton.Location=new Point(12,7);chat.Controls.Add(characterButton);
        var title=new Label{Text="가현",Location=new Point(50,13),Size=new Size(180,22),Font=new Font("Segoe UI",10.5f,FontStyle.Bold),ForeColor=Color.White,BackColor=chat.BackColor};chat.Controls.Add(title);
        moreButton=Button("more","더 보기",(s,e)=>ToggleControls());moreButton.Location=new Point(278,7);chat.Controls.Add(moreButton);
        closeChatButton=Button("close","채팅 닫기",(s,e)=>ToggleChat());closeChatButton.Location=new Point(318,7);chat.Controls.Add(closeChatButton);
        history.ReadOnly=true;history.BorderStyle=BorderStyle.None;history.BackColor=chat.BackColor;history.ForeColor=Color.White;history.Font=new Font("Segoe UI",10);chat.Controls.Add(history);
        input.BorderStyle=BorderStyle.None;input.BackColor=chat.BackColor;input.ForeColor=Color.White;input.Font=new Font("Segoe UI",10.5f);input.AccessibleName="가현에게 메시지 보내기";chat.Controls.Add(input);
        SendMessage(input.Handle,0x1501,new IntPtr(1),"가현에게 메시지 보내기");
        input.KeyDown+=async(s,e)=>{if(e.KeyCode==Keys.Enter){e.SuppressKeyPress=true;await Send();}};
        var send=Button("send","보내기",async(s,e)=>await Send());send.Name="send";send.ForeColor=ConversationDesign.Accent;chat.Controls.Add(send);
        mic=Button("mic-off","마이크 켜기",async(s,e)=>await Microphone());chat.Controls.Add(mic);
        sound=Button("sound","스피커 켜기 또는 끄기",(s,e)=>{soundOn=!soundOn;sound.Text=soundOn?"":"×";if(!soundOn){speakingUntil=DateTime.MinValue;if(player!=null)player.Stop();}sound.Invalidate();});sound.Text="×";chat.Controls.Add(sound);
        reactButton=Button("react","캐릭터 반응",(s,e)=>React());chat.Controls.Add(reactButton);
        activity.BackColor=chat.BackColor;activity.ForeColor=ConversationDesign.Muted;activity.Font=new Font("Segoe UI",9);chat.Controls.Add(activity);
        expand=Button("up","대화 펼치기",(s,e)=>{expanded=!expanded;LayoutPanels();});expand.Name="expand";chat.Controls.Add(expand);
        chat.FormClosing+=(s,e)=>{if(e.CloseReason==CloseReason.UserClosing){e.Cancel=true;ToggleChat();}};
        MouseDoubleClick+=(s,e)=>{if(e.Button==MouseButtons.Left)React();};
        MouseDown+=(s,e)=>{drag=e.Location;rotatedDrag=false;if(e.Button==MouseButtons.Left&&!dragLocked){recoveryTimer.Stop();pointerDragging=true;dragPointer=Cursor.Position;dragOrigin=Location;Capture=true;}};
        MouseUp+=(s,e)=>{if(e.Button==MouseButtons.Left&&pointerDragging){pointerDragging=false;Capture=false;RecoverAfterDrag();}};
        MouseCaptureChanged+=(s,e)=>{if(pointerDragging&&!Capture){pointerDragging=false;RecoverAfterDrag();}};
        recoveryTimer.Tick+=(s,e)=>{double t=(DateTime.UtcNow-recoveryBegan).TotalSeconds/.28,f=1-Math.Pow(1-Math.Min(1,t),3);Location=new Point((int)Math.Round(recoveryStart.X+(recoveryTarget.X-recoveryStart.X)*f),(int)Math.Round(recoveryStart.Y+(recoveryTarget.Y-recoveryStart.Y)*f));LayoutPanels();if(t>=1)recoveryTimer.Stop();};
        FormClosed+=(s,e)=>recoveryTimer.Dispose();
        MouseMove+=(s,e)=>{if(!dragLocked&&(e.Button==MouseButtons.Left||e.Button==MouseButtons.Right)){if(e.Button==MouseButtons.Right){rotatedDrag=true;yaw=Math.Max(-75,Math.Min(75,yaw-(e.X-drag.X)*.35f));drag=e.Location;PublishYaw(false);}else{if(pointerDragging){var cursor=Cursor.Position;Location=new Point(dragOrigin.X+cursor.X-dragPointer.X,dragOrigin.Y+cursor.Y-dragPointer.Y);LayoutPanels();}}}};
        MouseWheel+=(s,e)=>ChangeScale(e.Delta>0?.1f:-.1f);
        var menu=new ContextMenuStrip();
        menu.Items.Add("가현 보이기/숨기기",null,(s,e)=>ToggleVisibility());
        var lockItem=new ToolStripMenuItem("직접 드래그 잠금"){CheckOnClick=true};lockItem.CheckedChanged+=(s,e)=>SetDragLock(lockItem.Checked);menu.Items.Add(lockItem);
        menu.Items.Add("항상 위",null,(s,e)=>TogglePin());menu.Items.Add("애니메이션 화면 일시정지",null,(s,e)=>TogglePause());
        menu.Items.Add(new ToolStripSeparator());menu.Items.Add("크게",null,(s,e)=>ChangeScale(.1f));menu.Items.Add("작게",null,(s,e)=>ChangeScale(-.1f));menu.Items.Add("정위치 (위치·크기·회전)",null,(s,e)=>ResetPlacement());
        menu.Items.Add(new ToolStripSeparator());menu.Items.Add("가현 종료",null,(s,e)=>Close());
        menu.Opening+=(s,e)=>{if(rotatedDrag){e.Cancel=true;rotatedDrag=false;return;}((ToolStripMenuItem)menu.Items[2]).Checked=pinned;((ToolStripMenuItem)menu.Items[3]).Checked=paused;};
        ContextMenuStrip=menu;tray=new NotifyIcon{Icon=SystemIcons.Application,Text="가현",Visible=true,ContextMenuStrip=menu};tray.DoubleClick+=(s,e)=>ToggleVisibility();
        Shown+=(s,e)=>{chat.Show();LayoutPanels();timer.Start();};
        FormClosed+=(s,e)=>{timer.Stop();recordingLimit.Stop();mciSendString("close gahyeonMic",null,0,IntPtr.Zero);if(player!=null)player.Stop();if(picker!=null)picker.Dispose();pauseButton.Dispose();pinButton.Dispose();controls.Dispose();bubble.Dispose();chat.Dispose();tray.Dispose();tips.Dispose();if(view!=null)view.Dispose();if(memory!=null)memory.Dispose();http.Dispose();};
        timer.Tick+=(s,e)=>{UpdateInteraction();Frame();};recordingLimit.Tick+=async(s,e)=>{recordingLimit.Stop();if(recording)await Microphone();};
    }
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr h,int msg,IntPtr w,string text);
    [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr h,int index);
    [DllImport("user32.dll")] static extern int SetWindowLong(IntPtr h,int index,int value);
    void SetDragLock(bool locked) {dragLocked=locked;int style=GetWindowLong(Handle,-20);SetWindowLong(Handle,-20,locked?style|0x20:style&~0x20);}
    void ToggleChat(){if(chat.Visible){chat.Hide();if(picker!=null)picker.Close();bubble.Show();}else{chat.Show();LayoutPanels();input.Focus();}}
    void ToggleControls() {
        var menu=new ContextMenuStrip{BackColor=ConversationDesign.Surface,ForeColor=Color.White};
        menu.Items.Add("캐릭터 선택",null,(s,e)=>ShowCharacters());menu.Items.Add("캐릭터 반응",null,(s,e)=>React());
        bool systemMotion=true;SystemParametersInfo(0x1042,0,out systemMotion,0);
        var motion=new ToolStripMenuItem("동작 줄이기"){Checked=reducedMotion||!systemMotion,Enabled=systemMotion,ToolTipText=systemMotion?"":"Windows 애니메이션 꺼짐"};motion.Click+=(s,e)=>{reducedMotion=!reducedMotion;};menu.Items.Add(motion);
        var pin=new ToolStripMenuItem("항상 위"){Checked=pinned};pin.Click+=(s,e)=>TogglePin();menu.Items.Add(pin);
        var pause=new ToolStripMenuItem("애니메이션 화면 일시정지"){Checked=paused};pause.Click+=(s,e)=>TogglePause();menu.Items.Add(pause);
        menu.Items.Add("정위치 (위치·크기·회전)",null,(s,e)=>ResetPlacement());
        menu.Items.Add("화면 새로고침",null,(s,e)=>{crop=Rectangle.Empty;sequence=0;timer.Start();Frame();});
        menu.Items.Add("가현 종료",null,(s,e)=>Close());menu.Closed+=(s,e)=>BeginInvoke(new Action(()=>menu.Dispose()));menu.Show(chat,new Point(278,44));
    }
    void TogglePause() {
        paused=!paused;pauseButton.Symbol=paused?"play":"pause";
        pauseButton.AccessibleName=paused?"애니메이션 화면 재개":"애니메이션 화면 일시정지";
        tips.SetToolTip(pauseButton,pauseButton.AccessibleName);pauseButton.Invalidate();
    }
    void TogglePin() {pinned=!pinned;TopMost=controls.TopMost=bubble.TopMost=chat.TopMost=pinned;pinButton.ForeColor=pinned?Color.Cyan:Color.Gray;if(picker!=null)picker.TopMost=pinned;}
    void ToggleVisibility() {characterHidden=!characterHidden;if(characterHidden){Hide();controls.Hide();bubble.Hide();chat.Hide();if(picker!=null)picker.Close();}else{Show();chat.Show();LayoutPanels();}}
    void ChangeScale(float delta) {if(pointerDragging)return;recoveryTimer.Stop();if(!zoomCenter.HasValue){zoomChatOnRight=chat.Left+chat.Width/2>=Left+Width*(bodyBounds.X+bodyBounds.Width/2);zoomCenter=new PointF(Left+Width*(bodyBounds.X+bodyBounds.Width/2),Top+Height*(bodyBounds.Y+bodyBounds.Height/2));}scale=Math.Max(.65f,Math.Min(1.35f,scale+delta));sequence=0;bool restore=paused;paused=false;Frame();paused=restore;LayoutPanels();}
    void ResetPlacement() {yaw=0;PublishYaw(true);ChangeScale(1-scale);var area=Screen.FromControl(this).WorkingArea;Location=new Point(area.Right-Width-18,area.Bottom-Height-18);LayoutPanels();}
    void PublishYaw(bool reset) {
        try {using(var control=MemoryMappedFile.OpenExisting("{36CB1D68-2643-421D-85B1-61FCCFDA0402}"))using(var data=control.CreateViewAccessor(0,64)) {
            if(data.ReadUInt32(0)!=0x47484354)throw new IOException("캐릭터 런타임에 연결할 수 없습니다.");
            data.Write(8,yaw);data.Write(16,data.ReadUInt64(16)+1);if(reset)data.Write(24,data.ReadUInt64(24)+1);
        }}catch(Exception error){Append("시스템",error.Message);}
    }
    void ShowCharacters() {
        if(picker!=null&&!picker.IsDisposed){picker.Close();return;}
        try {
            uint current=appliedModel==UInt32.MaxValue?0:appliedModel;
            picker=new RosterPicker(current,SelectCharacter){TopMost=pinned};
            var area=Screen.FromControl(chat).WorkingArea;area.Inflate(-8,-8);
            picker.Location=new Point(Math.Max(area.Left,Math.Min(chat.Left,area.Right-picker.Width)),Math.Max(area.Top,Math.Min(chat.Top,area.Bottom-picker.Height)));
            picker.Show();
        }catch(Exception error){Append("시스템",error.Message);}
    }
    void SelectCharacter(uint index) {
        if(index>=8)return;
        try {
            using(var control=MemoryMappedFile.OpenExisting("{36CB1D68-2643-421D-85B1-61FCCFDA0402}"))
            using(var data=control.CreateViewAccessor(0,64)) {
                if(data.ReadUInt32(0)!=0x47484354 || data.ReadUInt32(44)!=0x524F5354)throw new IOException("캐릭터 런타임에 연결할 수 없습니다.");
                data.Write(32,index);
            }
        } catch(Exception error){Append("시스템",error.Message);}
    }
    static int ZoomChatShift(RectangleF body,Rectangle workArea,int chatWidth,bool onRight) {
        workArea.Inflate(-8,-8);int reserve=chatWidth+12;
        if(body.Width+reserve>workArea.Width)return 0;
        float left=workArea.Left+(onRight?0:reserve),right=workArea.Right-body.Width-(onRight?reserve:0);
        return (int)Math.Round(Math.Min(Math.Max(body.Left,left),right)-body.Left);
    }
    static Point RecoveredOrigin(Rectangle window,Rectangle body,Rectangle workArea) {
        workArea.Inflate(-8,-8);int head=Math.Min(body.Height,Math.Min(140,Math.Max(72,(int)(body.Height*.22))));
        int x=body.Width>workArea.Width?workArea.Left+(workArea.Width-body.Width)/2:Math.Min(Math.Max(body.Left,workArea.Left),workArea.Right-body.Width);
        int y=Math.Min(Math.Max(body.Top,workArea.Top),workArea.Bottom-head);
        return new Point(window.Left+x-body.Left,window.Top+y-body.Top);
    }
    void RecoverAfterDrag() {
        recoveryTimer.Stop();var body=new Rectangle(Left+(int)(Width*bodyBounds.X),Top+(int)(Height*bodyBounds.Y),(int)(Width*bodyBounds.Width),(int)(Height*bodyBounds.Height));
        recoveryStart=Location;recoveryTarget=RecoveredOrigin(Bounds,body,Screen.FromPoint(Cursor.Position).WorkingArea);
        if(recoveryTarget==recoveryStart)return;
        bool motion=true;SystemParametersInfo(0x1042,0,out motion,0);
        if(reducedMotion||!motion){Location=recoveryTarget;LayoutPanels();return;}
        recoveryBegan=DateTime.UtcNow;recoveryTimer.Start();
    }
    void LayoutPanels() {
        if(layoutBusy)return;layoutBusy=true;
        try {
            var area=Screen.FromControl(this).WorkingArea;area.Inflate(-8,-8);
            int width=ConversationDesign.Number("chatWidth",360),height=ConversationDesign.Number(expanded?"expandedHeight":"chatHeight",expanded?440:280);
            var body=new Rectangle(Left+(int)(Width*bodyBounds.X),Top+(int)(Height*bodyBounds.Y),(int)(Width*bodyBounds.Width),(int)(Height*bodyBounds.Height));
            int right=body.Right+12,left=body.Left-12-width,preferred=right+width<=area.Right?right:left>=area.Left?left:right;
            chat.ClientSize=new Size(width,height);chat.Location=new Point(Math.Max(area.Left,Math.Min(preferred,area.Right-width)),Math.Max(area.Top,Math.Min(body.Bottom-(int)(body.Height*.22)-height,area.Bottom-height)));
            int bubbleRight=Left+(int)(Width*bodySide)+12,bubbleX=bubbleRight+36<=area.Right?bubbleRight:body.Left-48;
            bubble.Location=new Point(Math.Max(area.Left,Math.Min(bubbleX,area.Right-36)),Math.Max(area.Top,Math.Min(body.Top+body.Height/2-18,area.Bottom-36)));
            if(chat.Visible)bubble.Hide();else if(!characterHidden)bubble.Show();
            if(panelLayoutSize==new Size(width,height))return;
            panelLayoutSize=new Size(width,height);
            history.SetBounds(16,52,width-32,height-156);history.Visible=true;
            input.SetBounds(16,height-80,width-74,28);chat.Controls["send"].SetBounds(width-42,height-83,30,30);
            mic.SetBounds(12,height-42,30,30);sound.SetBounds(50,height-42,30,30);reactButton.SetBounds(88,height-42,30,30);
            activity.SetBounds(130,height-36,175,20);expand.SetBounds(width-42,height-42,30,30);
            ((IconButton)expand).Symbol=expanded?"down":"up";expand.AccessibleName=expanded?"대화 접기":"대화 펼치기";tips.SetToolTip(expand,expand.AccessibleName);expand.Invalidate();chat.Invalidate();
        } finally {layoutBusy=false;}
    }
    void Append(string role,string text) {history.AppendText(role+"\n"+text+"\n\n");LayoutPanels();history.SelectionStart=history.TextLength;history.ScrollToCaret();}
    void React(){reactionStarted=DateTime.UtcNow;nextIdleReaction=reactionStarted.AddSeconds(45);}
    void UpdateInteraction(){
        var now=DateTime.UtcNow;
        string phase=recording?"듣는 중":busy?"음성 처리 중":!input.Enabled?"응답 대기":now<speakingUntil?"말하는 중":"";
        if(activity.Text!=phase)activity.Text=phase;
        ((IconButton)mic).Symbol=recording?"mic":"mic-off";mic.ForeColor=recording?ConversationDesign.Accent:Color.White;mic.AccessibleName=recording?"마이크 끄기":"마이크 켜기";tips.SetToolTip(mic,mic.AccessibleName);mic.Invalidate();
        bool systemAnimation=true;SystemParametersInfo(0x1042,0,out systemAnimation,0);
        if(Single.IsNaN(lastBaseYaw)||lastBaseYaw!=yaw){lastBaseYaw=yaw;reactionYaw=Single.NaN;reactionStarted=DateTime.MinValue;nextIdleReaction=now.AddSeconds(45);}
        if(now>nextIdleReaction&&phase.Length==0)React();
        double offset=0,age=(now-reactionStarted).TotalSeconds,t=(now-new DateTime(2001,1,1,0,0,0,DateTimeKind.Utc)).TotalSeconds;
        if(!paused&&!reducedMotion&&systemAnimation){if(age>=0&&age<1.4)offset=Math.Sin(age/1.4*Math.PI*2)*10*Math.Sin(age/1.4*Math.PI);else if(phase=="듣는 중")offset=4;else if(phase=="응답 대기")offset=Math.Sin(t*1.6)*1.5;else if(phase=="말하는 중")offset=Math.Sin(t*3.2)*2.5;}
        float target=Math.Max(-75,Math.Min(75,yaw+(float)offset)),eased=paused||reducedMotion||!systemAnimation||Single.IsNaN(reactionYaw)?target:reactionYaw+(target-reactionYaw)*.22f;
        if(!Single.IsNaN(reactionYaw)&&Math.Abs(eased-reactionYaw)<=.02f)return;
        try{using(var control=MemoryMappedFile.OpenExisting("{36CB1D68-2643-421D-85B1-61FCCFDA0402}"))using(var data=control.CreateViewAccessor(0,64)){if(data.ReadUInt32(0)!=0x47484354)return;data.Write(8,eased);data.Write(16,data.ReadUInt64(16)+1);reactionYaw=eased;}}catch(FileNotFoundException){}
    }
    static double WaveSeconds(byte[] wav){
        int rate=0,bytes=0;
        for(int p=12;p+8<=wav.Length;){int size=BitConverter.ToInt32(wav,p+4);if(size<0||size>wav.Length-p-8)break;string tag=Encoding.ASCII.GetString(wav,p,4);if(tag=="fmt "&&size>=16)rate=BitConverter.ToInt32(wav,p+16);if(tag=="data")bytes=size;p+=8+size+(size%2);}
        return rate>0?(double)bytes/rate:0;
    }
    async Task<byte[]> Post(string path,byte[] data,string type) {
        using(var body=new ByteArrayContent(data)){body.Headers.ContentType=new System.Net.Http.Headers.MediaTypeHeaderValue(type);using(var r=await http.PostAsync(core.TrimEnd('/')+path,body)){r.EnsureSuccessStatusCode();return await r.Content.ReadAsByteArrayAsync();}}
    }
    async Task Send() {
        string text=input.Text.Trim();if(text.Length==0||!input.Enabled)return;input.Clear();input.Enabled=false;speakingUntil=DateTime.MinValue;if(player!=null)player.Stop();Append("나",text);
        try {
            var body=new {requestId="windows:"+Guid.NewGuid(),installationId=installation,displayName=Environment.UserName,characterId="gahyeon",message=text};
            var bytes=await Post("/gahyeon/desktop/conversations/"+session+"/messages",Encoding.UTF8.GetBytes(json.Serialize(body)),"application/json");
            var result=json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(Encoding.UTF8.GetString(bytes));string reply=Convert.ToString(result["content"]);Append("가현",reply);
            if(soundOn){var wav=await Post("/gahyeon/desktop/speech/synthesis",Encoding.UTF8.GetBytes(json.Serialize(new {index=0,text=reply,voiceProfile="gahyeon.assistant"})),"application/json");if(soundOn){if(player!=null)player.Stop();if(playing!=null)playing.Dispose();playing=new MemoryStream(wav);player=new SoundPlayer(playing);player.Play();speakingUntil=DateTime.UtcNow.AddSeconds(WaveSeconds(wav));}}
        } catch(Exception ex){Append("시스템",ex.Message);} finally{input.Enabled=true;}
    }
    async Task Microphone() {
        if(busy)return;
        if(!recording){
            if(player!=null)player.Stop();speakingUntil=DateTime.MinValue;int error=mciSendString("open new type waveaudio alias gahyeonMic",null,0,IntPtr.Zero);
            if(error==0)error=mciSendString("set gahyeonMic channels 1 samplespersec 16000 bitspersample 16 alignment 2 bytespersec 32000",null,0,IntPtr.Zero);
            if(error==0)error=mciSendString("record gahyeonMic",null,0,IntPtr.Zero);
            if(error!=0){mciSendString("close gahyeonMic",null,0,IntPtr.Zero);Append("시스템","마이크를 시작할 수 없습니다: "+error);return;}
            recording=true;mic.ForeColor=Color.Red;recordingLimit.Start();return;
        }
        recording=false;busy=true;recordingLimit.Stop();mic.ForeColor=Color.Orange;string path=Path.Combine(Path.GetTempPath(),Guid.NewGuid()+".wav");
        try{mciSendString("stop gahyeonMic",null,0,IntPtr.Zero);if(mciSendString("save gahyeonMic \""+path+"\"",null,0,IntPtr.Zero)!=0)throw new Exception("녹음 저장 실패");mciSendString("close gahyeonMic",null,0,IntPtr.Zero);
            var bytes=await Post("/gahyeon/desktop/speech/transcriptions",File.ReadAllBytes(path),"audio/wav");var result=json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(Encoding.UTF8.GetString(bytes));input.Text=Convert.ToString(result["transcript"]);await Send();
        }catch(Exception ex){Append("시스템",ex.Message);}finally{mciSendString("close gahyeonMic",null,0,IntPtr.Zero);if(File.Exists(path))File.Delete(path);busy=false;mic.ForeColor=Color.White;}
    }
    void Frame() {
        if(paused||characterHidden||pointerDragging||recoveryTimer.Enabled)return;
        try {
            try {using(var control=MemoryMappedFile.OpenExisting("{36CB1D68-2643-421D-85B1-61FCCFDA0402}"))using(var state=control.CreateViewAccessor(0,64)) {
                uint model=state.ReadUInt32(36);if(model!=appliedModel){appliedModel=model;crop=Rectangle.Empty;}
            }}catch(FileNotFoundException){}

            if(view==null){memory=MemoryMappedFile.OpenExisting(Frames,MemoryMappedFileRights.Read);view=memory.CreateViewAccessor(0,0,MemoryMappedFileAccess.Read);}
            long seq=view.ReadInt64(24);if(seq==0||seq==sequence)return;
            int w=view.ReadInt32(8),h=view.ReadInt32(12),stride=view.ReadInt32(16),active=view.ReadInt32(20);
            if(w!=1600||h!=1258||stride!=w*4||active<0||active>1)return;
            byte[] data=new byte[stride*h];Marshal.Copy(IntPtr.Add(view.SafeMemoryMappedViewHandle.DangerousGetHandle(),64+active*data.Length),data,0,data.Length);
            if(view.ReadInt64(24)!=seq||view.ReadInt32(20)!=active)return;
            int l=Math.Max(0,view.ReadInt32(40)-80),t=Math.Max(0,view.ReadInt32(44)-50),r=Math.Min(w,view.ReadInt32(48)+81),b=Math.Min(h,view.ReadInt32(52)+51);if(r<=l||b<=t)return;
            bool measureAnchors=crop.IsEmpty;
            if(crop.IsEmpty){crop=Rectangle.FromLTRB(l,t,r,b);contentHeight=(int)Math.Min(Screen.FromControl(this).WorkingArea.Height*.78,720);}
            l=crop.Left;t=crop.Top;r=crop.Right;b=crop.Bottom;
            using(var full=new Bitmap(w,h,PixelFormat.Format32bppPArgb)){
                var bits=full.LockBits(new Rectangle(0,0,w,h),ImageLockMode.WriteOnly,PixelFormat.Format32bppPArgb);Marshal.Copy(data,0,bits.Scan0,data.Length);full.UnlockBits(bits);
                int drawH=(int)(contentHeight*scale),drawW=(r-l)*drawH/(b-t);int insetX=(int)(24*scale),insetY=(int)(20*scale);int targetH=drawH+insetY*2,targetW=drawW+insetX*2;
                using(var frame=new Bitmap(targetW,targetH,PixelFormat.Format32bppPArgb)){
                    using(var g=Graphics.FromImage(frame)){g.CompositingMode=CompositingMode.SourceCopy;g.InterpolationMode=InterpolationMode.HighQualityBicubic;g.DrawImage(full,new Rectangle(insetX,insetY,drawW,drawH),new Rectangle(l,t,r-l,b-t),GraphicsUnit.Pixel);}
                    IntPtr screen=GetDC(IntPtr.Zero),dc=CreateCompatibleDC(screen),bitmap=frame.GetHbitmap(Color.FromArgb(0)),old=SelectObject(dc,bitmap);
                    var size=new Size(targetW,targetH);var pos=zoomCenter.HasValue?new Point((int)Math.Round(zoomCenter.Value.X-targetW*(bodyBounds.X+bodyBounds.Width/2)),(int)Math.Round(zoomCenter.Value.Y-targetH*(bodyBounds.Y+bodyBounds.Height/2))):Location;
                    int alphaL=w,alphaR=0,alphaT=h,alphaB=0,side=0;
                    // Sample the current torso band; anchors stay stable for each cropped model.
                    if(measureAnchors){
                        for(int yy=t;yy<b;yy+=2)for(int xx=l;xx<r;xx+=2)if(data[yy*stride+xx*4+3]>24){alphaL=Math.Min(alphaL,xx);alphaR=Math.Max(alphaR,xx);alphaT=Math.Min(alphaT,yy);alphaB=Math.Max(alphaB,yy);}
                        int mid=(alphaT+alphaB)/2,band=Math.Max(18,(alphaB-alphaT)/12);
                        for(int yy=Math.Max(t,mid-band);yy<Math.Min(b,mid+band);yy+=2)for(int xx=l;xx<r;xx+=2)if(data[yy*stride+xx*4+3]>24)side=Math.Max(side,xx);
                        if(alphaR>alphaL&&alphaB>alphaT){bodyBounds=new RectangleF((insetX+(alphaL-l)*(float)drawW/(r-l))/targetW,(insetY+(alphaT-t)*(float)drawH/(b-t))/targetH,(alphaR-alphaL)*(float)drawW/(r-l)/targetW,(alphaB-alphaT)*(float)drawH/(b-t)/targetH);bodySide=(insetX+(side-l)*(float)drawW/(r-l))/targetW;}
                    }
                    if(zoomCenter.HasValue&&chat.Visible){var body=new RectangleF(pos.X+targetW*bodyBounds.X,pos.Y+targetH*bodyBounds.Y,targetW*bodyBounds.Width,targetH*bodyBounds.Height);pos.X+=ZoomChatShift(body,Screen.FromControl(this).WorkingArea,chat.Width,zoomChatOnRight);}
                    var zero=Point.Empty;var blend=new Blend{Alpha=255,Format=1};
                    bool updated=UpdateLayeredWindow(Handle,screen,ref pos,ref size,dc,ref zero,0,ref blend,2);int updateError=Marshal.GetLastWin32Error();SelectObject(dc,old);DeleteObject(bitmap);DeleteDC(dc);ReleaseDC(IntPtr.Zero,screen);
                    if(!updated)throw new System.ComponentModel.Win32Exception(updateError);
                    if(Size!=size||Location!=pos||zoomCenter.HasValue){Bounds=new Rectangle(pos,size);zoomCenter=null;LayoutPanels();}
                }
            }
            sequence=seq;
        }catch(FileNotFoundException){}catch(Exception ex){timer.Stop();Append("시스템","캐릭터 표시 실패: "+ex.Message);}
    }
    [STAThread] static void Main(){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new GahyeonOverlay());}
}
