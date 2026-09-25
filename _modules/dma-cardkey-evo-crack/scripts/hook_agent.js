// ============================================================
//  hook_agent.js v2 — Evo_Crack.exe 动态探针 (Frida 17 API 修正版)
// ============================================================
'use strict';
let T0 = Date.now();
function ts(){ return ((Date.now()-T0)/1000).toFixed(3); }
function send2(tag, obj){ try{ send({tag:tag, t:ts(), data:obj}); }catch(e){} }
function w(s){ send2('line', {msg: String(s)}); }
function esc(s){ try{ return s===null||s===undefined ? String(s) : String(s).replace(/\\/g,'/'); }catch(e){ return '<unreadable>'; } }
function hexdump_u8(p, len, max){
  try{
    const n = Math.min(len, max||512);
    const b = new Uint8Array(p.readByteArray(n));
    let hx='', asc='';
    for(let i=0;i<b.length;i++){
      hx += ('0'+b[i].toString(16)).slice(-2) + ((i%32===31)?'\n  ':' ');
      asc += (b[i]>=32 && b[i]<127) ? String.fromCharCode(b[i]) : '.';
    }
    return {hex:hx, ascii:asc};
  }catch(e){ return {hex:'<fail '+e+'>', ascii:''}; }
}
// ---- Frida 17 兼容导出解析 ----
function resolve(modName, expName){
  if (modName) {
    try { const m = Process.getModuleByName(modName); const p = m.getExportByName(expName); if (p) return p; } catch(e){}
  }
  try { const p2 = Module.getGlobalExportByName(expName); if (p2) return p2; } catch(e){}
  return null;
}
let HOOKED = [], FAILED = [];
function hookExport(modName, expName, name, onEnter, onLeave){
  const p = resolve(modName, expName);
  if (!p) { FAILED.push(modName+'!'+expName); return false; }
  try{
    Interceptor.attach(p, {
      onEnter: function(args){ try{ if(onEnter) onEnter.call(this,args); }catch(e){} },
      onLeave: function(rv){ try{ if(onLeave) onLeave.call(this,rv); else if(this._ol) this._ol.call(this,rv); }catch(e){} }
    });
    HOOKED.push(name||expName);
    return true;
  }catch(e){ FAILED.push(name+'@attach:'+e); return false; }
}
// 多模块尝试
function hookAny(mods, expName, name, onEnter, onLeave){
  for(const m of mods){ if (hookExport(m, expName, name+':'+m, onEnter, onLeave)) return true; }
  return false;
}
function wideStr(p, max){ try{ return p.isNull()?null:p.readUtf16String(Math.min(max||512, 8192)); }catch(e){ return '<bad>'; } }
function ansiStr(p, max){ try{ return p.isNull()?null:p.readAnsiString(Math.min(max||512, 8192)); }catch(e){ return '<bad>'; } }

const CRT = ['ucrtbase.dll','msvcrt.dll','api-ms-win-crt-stdio-l1-1-0.dll','api-ms-win-crt-runtime-l1-1-0.dll'];

// ---------- 0. 退出拦截: 冻结进程给 Python 时间 dump ----------
let EXITING = false, RELEASED = false, EXIT_HOOKED = false;
function installExitGates(){
  const tries = [
    ['KERNEL32.dll','ExitProcess'], ['ntdll.dll','RtlExitUserProcess'], ['ntdll.dll','NtTerminateProcess'],
    ['KERNEL32.dll','TerminateProcess'], ['ntdll.dll','RtlExitUserThread']
  ];
  for(const [m,e] of tries){
    if (hookExport(m,e,'EXIT:'+e, function(a){
      if (EXITING) return;
      EXITING = true;
      const code = a.length>1 ? (e==='TerminateProcess'? a[2].toInt32() : a[0].toInt32()) : 0;
      w('!!! PROCESS EXITING via '+m+'!'+e+' code='+code+' — freezing for dump');
      send2('EXITGATE', {where: m+'!'+e, code: code});
      try {
        const mainMod = Process.getModuleByName('Evo_Crack.exe');
        w('!!! auto-dumping main module: ' + mainMod.base + ' size=0x' + mainMod.size.toString(16));
        const r1 = saveRange('main_at_exit.bin', mainMod.base, mainMod.size);
        w('!!! auto-dump main -> ' + r1);
        const rwx = Process.enumerateRanges('rwx');
        w('!!! rwx regions: ' + rwx.length);
        let idx = 0;
        rwx.forEach(function(r){
          if (r.size >= 0x1000 && idx < 40){
            const r2 = saveRange('exit_rwx_' + idx + '_' + r.base.toString().replace('0x','') + '.bin', r.base, Math.min(r.size, 64*1024*1024));
            w('!!! rwx[' + idx + '] ' + r.base + ' size=0x' + r.size.toString(16) + ' -> ' + r2);
            idx++;
          }
        });
      } catch(e){ w('!!! auto-dump fail ' + e); }
      const t0 = Date.now();
      while(!RELEASED && (Date.now()-t0) < 25000){ }
      w('!!! released after '+((Date.now()-t0)/1000).toFixed(1)+'s');
    }, null)) { EXIT_HOOKED = true; }
  }
  // CRT exit
  hookAny(CRT,'exit','EXIT:exit',function(a){
    if (EXITING) return; EXITING = true;
    w('!!! CRT exit('+a[0].toInt32()+') — freezing');
    send2('EXITGATE', {where:'exit', code:a[0].toInt32()});
    const t0=Date.now(); while(!RELEASED && (Date.now()-t0)<90000){}
  }, null);
}

// ---------- 1. 输入捕获 ----------
function hookInput(){
  hookAny(CRT,'getchar','getchar',null,function(rv){ w('getchar -> '+rv.toInt32()+' ('+JSON.stringify(String.fromCharCode(rv.toInt32()&0xff))+')'); });
  hookAny(CRT,'_getch','_getch',null,function(rv){ w('_getch -> '+rv.toInt32()); });
  hookAny(CRT,'fgets','fgets',function(a){ this.b=a[0]; this.n=a[1].toInt32(); }, function(rv){
    if(!rv.isNull()) w('fgets(n='+this.n+') -> '+JSON.stringify(ansiStr(this.b,this.n)));
  });
  hookAny(CRT,'gets','gets',function(a){ this.b=a[0]; }, function(rv){ w('gets -> '+JSON.stringify(ansiStr(this.b,512))); });
  hookAny(CRT,'scanf','scanf',function(a){ this.f=ansiStr(a[0],128); this.p0=a[1]; }, function(){
    send2('SCANF', {fmt:this.f, arg0: ansiStr(this.p0,1024)});
  });
  hookAny(CRT,'_scanf_s','_scanf_s',function(a){ this.f=ansiStr(a[0],128); this.p0=a[1]; }, function(){
    send2('SCANF', {fmt:this.f, arg0: ansiStr(this.p0,1024)});
  });
  hookAny(CRT,'std::cin','cin',null,null);
  hookExport('KERNEL32.dll','ReadConsoleW','ReadConsoleW',function(a){ this.b=a[1]; this.n=a[2].toInt32(); }, function(rv){
    if(rv.toInt32()!==0) w('ReadConsoleW -> '+JSON.stringify(wideStr(this.b,this.n)));
  });
  hookExport('KERNEL32.dll','ReadConsoleA','ReadConsoleA',function(a){ this.b=a[1]; this.n=a[2].toInt32(); }, function(rv){
    if(rv.toInt32()!==0) w('ReadConsoleA -> '+JSON.stringify(ansiStr(this.b,this.n)));
  });
}

// ---------- 2. 控制台输出 ----------
function hookConsole(){
  hookExport('KERNEL32.dll','WriteConsoleW','WriteConsoleW',function(a){
    const s = wideStr(a[1], a[2].toInt32()+2); if(s) w('CONSOLE> '+s.replace(/\r?\n/g,'\\n'));
  });
  hookExport('KERNEL32.dll','WriteConsoleA','WriteConsoleA',function(a){
    const s = ansiStr(a[1], a[2].toInt32()+2); if(s) w('CONSOLE> '+s.replace(/\r?\n/g,'\\n'));
  });
  const hOut = (function(){ try{ return Module.getGlobalExportByName('GetStdHandle'); }catch(e){ return null; } })();
  let STD_OUT = null, STD_ERR = null;
  try{ const g = resolve('KERNEL32.dll','GetStdHandle'); if(g){ STD_OUT = new NativeFunction(g,'pointer',['int32'])(-11); STD_ERR = new NativeFunction(g,'pointer',['int32'])(-12);
       w('stdout handle = '+STD_OUT+', stderr = '+STD_ERR); } }catch(e){}
  hookExport('KERNEL32.dll','WriteFile','WriteFile',function(a){
    const h = a[0]; const n = a[2].toInt32();
    let isOut = false;
    try{ if(STD_OUT && h.equals(STD_OUT)) isOut=true; if(STD_ERR && h.equals(STD_ERR)) isOut=true; }catch(e){}
    if (h.toInt32() === -11 || h.toInt32() === -12) isOut = true;
    if (isOut && n>0 && n<16384){
      const s = ansiStr(a[1], n); if(s) w('STDOUT> '+s.replace(/\r?\n/g,'\\n'));
    }
  });
}

// ---------- 3. 文件系统 ----------
let FH = {};
function hookFiles(){
  hookExport('KERNEL32.dll','CreateFileW','CreateFileW',function(a){
    this.path = wideStr(a[0],1024); this.acc=a[1].toInt32()>>>0; this.disp=a[4].toInt32()>>>0;
  }, function(rv){
    FH[rv.toString()] = this.path;
    w('CreateFileW("'+esc(this.path)+'", acc=0x'+this.acc.toString(16)+', disp='+this.disp+') -> '+rv);
  });
  hookExport('KERNEL32.dll','CreateFileA','CreateFileA',function(a){ this.path=ansiStr(a[0],1024); }, function(rv){
    FH[rv.toString()] = this.path; w('CreateFileA("'+esc(this.path)+'") -> '+rv);
  });
  hookExport('KERNEL32.dll','WriteFile','WriteFile',function(a){
    const h=a[0].toString(), n=a[2].toInt32(); const path = FH[h];
    if (path && n>0){
      const hx = hexdump_u8(a[1], n, 1024);
      send2('WRITEFILE', {path:path, size:n, hex:hx.hex, ascii:hx.ascii});
    }
  });
  hookExport('KERNEL32.dll','ReadFile','ReadFile',function(a){
    const h=a[0].toString(), n=a[2].toInt32(); const path=FH[h];
    if (path && n>0){ this.path=path; this.b=a[1]; this.n=n; this.lp=a[3];
      this._ol = function(){ let got=this.n; try{ if(!this.lp.isNull()) got=this.lp.readU32(); }catch(e){}
        if(got>0&&got<0x200000){ const hx=hexdump_u8(this.b,got,512); send2('READFILE',{path:this.path,size:got,hex:hx.hex,ascii:hx.ascii}); } };
    }
  });
  hookExport('KERNEL32.dll','CreateDirectoryW','CreateDirectoryW',function(a){ w('CreateDirectoryW("'+esc(wideStr(a[0],1024))+'")'); });
  hookExport('KERNEL32.dll','CopyFileW','CopyFileW',function(a){ w('CopyFileW("'+esc(wideStr(a[0],1024))+'") -> ("'+esc(wideStr(a[1],1024))+'")'); });
  hookExport('KERNEL32.dll','MoveFileW','MoveFileW',function(a){ w('MoveFileW("'+esc(wideStr(a[0],1024))+'") -> ("'+esc(wideStr(a[1],1024))+'")'); });
  hookExport('KERNEL32.dll','DeleteFileW','DeleteFileW',function(a){ w('DeleteFileW("'+esc(wideStr(a[0],1024))+'")'); });
  hookExport('KERNEL32.dll','GetFileSizeEx','GetFileSizeEx',null,null);
  hookExport('KERNEL32.dll','SetFilePointer','SetFilePointer',function(a){ w('SetFilePointer('+esc(FH[a[0].toString()]||a[0])+' lo='+a[1].toInt32()+')'); });
  // 目录枚举
  hookExport('KERNEL32.dll','FindFirstFileW','FindFirstFileW',function(a){ w('FindFirstFileW("'+esc(wideStr(a[0],1024))+'")'); });
  hookExport('KERNEL32.dll','FindNextFileW','FindNextFileW',null,null);
}

// ---------- 4. 内存 / 模块 / 补丁 ----------
let VP = [];
function hookMem(){
  hookExport('KERNEL32.dll','VirtualProtect','VirtualProtect',function(a){
    const prot=a[2].toInt32()>>>0;
    const tag = (prot&0x40)?' <<< RWX':'';
    VP.push({addr:a[0].toString(), size:a[1].toInt32(), prot:prot});
    w('VirtualProtect(addr='+a[0]+', size=0x'+a[1].toInt32().toString(16)+', prot=0x'+prot.toString(16)+')'+tag);
  });
  hookExport('KERNEL32.dll','VirtualAlloc','VirtualAlloc',function(a){ this.sz=a[1].toInt32()>>>0; this.pr=a[3].toInt32()>>>0; }, function(rv){
    if(this.sz>0x1000) w('VirtualAlloc(size=0x'+this.sz.toString(16)+', prot=0x'+this.pr.toString(16)+') -> '+rv);
  });
  hookExport('KERNEL32.dll','LoadLibraryW','LoadLibraryW',function(a){ w('LoadLibraryW("'+esc(wideStr(a[0],512))+'")'); });
  hookExport('KERNEL32.dll','LoadLibraryA','LoadLibraryA',function(a){ w('LoadLibraryA("'+esc(ansiStr(a[0],512))+'")'); });
  hookExport('KERNEL32.dll','LoadLibraryExW','LoadLibraryExW',function(a){ w('LoadLibraryExW("'+esc(wideStr(a[0],512))+'")'); });
  hookExport('KERNEL32.dll','GetProcAddress','GetProcAddress',function(a){
    let nm = null;
    try{ if(!a[1].isNull() && a[1].compare(ptr('0x10000'))>0) nm = ansiStr(a[1],128); }catch(e){}
    w('GetProcAddress(h='+a[0]+', '+(nm?('"'+esc(nm)+'"'):('ord='+a[1].toInt32()))+')');
  });
  hookExport('KERNEL32.dll','WriteProcessMemory','WriteProcessMemory',function(a){
    const hx=hexdump_u8(a[2], a[3].toInt32(), 512);
    send2('WPM',{proc:a[0].toString(), addr:a[1].toString(), size:a[3].toInt32(), hex:hx.hex, ascii:hx.ascii});
  });
  hookExport('KERNEL32.dll','ReadProcessMemory','ReadProcessMemory',function(a){ w('ReadProcessMemory(proc='+a[0]+', addr='+a[1]+', size=0x'+a[2].toInt32().toString(16)+')'); });
  hookExport('KERNEL32.dll','FlushInstructionCache','FlushInstructionCache',function(a){ w('FlushInstructionCache(addr='+a[0]+', size=0x'+a[1].toInt32().toString(16)+')'); });
  // 内存映射/节
  hookExport('KERNEL32.dll','MapViewOfFile','MapViewOfFile',null,null);
  hookExport('KERNEL32.dll','CreateFileMappingW','CreateFileMappingW',null,null);
}

// ---------- 5. 网络 ----------
function hookNet(){
  hookExport('WS2_32.dll','WSAStartup','WSAStartup',null,null);
  hookExport('WS2_32.dll','connect','connect',function(a){
    try{ const sa=a[1]; const fam=sa.readU16();
      if(fam===2){ const port=(sa.add(2).readU8()<<8)|sa.add(3).readU8();
        const ip=[sa.add(4).readU8(),sa.add(5).readU8(),sa.add(6).readU8(),sa.add(7).readU8()].join('.');
        w('connect -> '+ip+':'+port);
      } else if(fam===23){ w('connect -> IPv6'); } else { w('connect family='+fam); }
    }catch(e){ w('connect sock='+a[0]); }
  });
  hookExport('WS2_32.dll','getaddrinfo','getaddrinfo',function(a){ w('getaddrinfo("'+esc(ansiStr(a[0],256))+'", "'+esc(ansiStr(a[1],64))+'")'); });
  hookExport('WS2_32.dll','gethostbyname','gethostbyname',function(a){ w('gethostbyname("'+esc(ansiStr(a[0],256))+'")'); });
  hookExport('DNSAPI.dll','DnsQuery_A','DnsQuery_A',function(a){ w('DnsQuery_A("'+esc(ansiStr(a[0],256))+'")'); });
  hookExport('DNSAPI.dll','DnsQuery_W','DnsQuery_W',function(a){ w('DnsQuery_W("'+esc(wideStr(a[0],256))+'")'); });
  hookExport('WS2_32.dll','send','send',function(a){
    const n=a[2].toInt32(); const hx=hexdump_u8(a[1],n,2048);
    send2('SEND',{sock:a[0].toString(), size:n, hex:hx.hex, ascii:hx.ascii});
  });
  hookExport('WS2_32.dll','sendto','sendto',function(a){
    const n=a[2].toInt32(); const hx=hexdump_u8(a[1],n,2048);
    send2('SENDTO',{size:n, hex:hx.hex, ascii:hx.ascii});
  });
  hookExport('WS2_32.dll','WSASend','WSASend',function(a){
    try{ const b=a[1]; const c=a[2].toInt32();
      for(let i=0;i<Math.min(c,4);i++){ const len=b.add(i*16).readU32(); const p=b.add(i*16+8).readPointer();
        const hx=hexdump_u8(p,len,2048); send2('WSASEND',{idx:i,size:len,hex:hx.hex,ascii:hx.ascii}); }
    }catch(e){}
  });
  hookExport('WS2_32.dll','recv','recv',function(a){ this.b=a[1]; this.n=a[2].toInt32(); }, function(rv){
    const got=rv.toInt32(); if(got>0){ const hx=hexdump_u8(this.b,got,2048); send2('RECV',{size:got,hex:hx.hex,ascii:hx.ascii}); }
  });
  hookExport('WS2_32.dll','WSARecv','WSARecv',function(a){
    try{ const b=a[1]; this.b=b.add(8).readPointer(); this.n=b.readU32(); this.lp=a[3]; }catch(e){}
  }, function(){
    try{ const got=this.lp.isNull()?this.n:this.lp.readU32();
      if(got>0&&got<=1<<20){ const hx=hexdump_u8(this.b,got,2048); send2('WSARECV',{size:got,hex:hx.hex,ascii:hx.ascii}); } }catch(e){}
  });
  // WinHTTP
  hookExport('WINHTTP.dll','WinHttpOpen','WinHttpOpen',function(a){ w('WinHttpOpen(ua="'+esc(wideStr(a[0],512))+'")'); });
  hookExport('WINHTTP.dll','WinHttpConnect','WinHttpConnect',function(a){ w('WinHttpConnect(host="'+esc(wideStr(a[1],512))+'", port='+a[2].toInt32()+')'); });
  hookExport('WINHTTP.dll','WinHttpOpenRequest','WinHttpOpenRequest',function(a){
    w('WinHttpOpenRequest(verb="'+esc(wideStr(a[1],32))+'", path="'+esc(wideStr(a[2],2048))+'", ver="'+esc(wideStr(a[5],32))+'")');
  });
  hookExport('WINHTTP.dll','WinHttpSendRequest','WinHttpSendRequest',function(a){
    const n=a[3].toInt32(); const hdr=wideStr(a[0],512);
    let body=null; if(n>0&&n<0x200000){ const hx=hexdump_u8(a[2],n,4096); body={size:n,hex:hx.hex,ascii:hx.ascii}; }
    send2('WinHttpSendRequest',{headers:hdr, total:a[4].toInt32(), body:body});
  });
  hookExport('WINHTTP.dll','WinHttpReceiveResponse','WinHttpReceiveResponse',null,null);
  hookExport('WINHTTP.dll','WinHttpReadData','WinHttpReadData',function(a){ this.b=a[1]; this.n=a[2].toInt32(); this.lp=a[3]; }, function(){
    try{ const got=this.lp.isNull()?this.n:this.lp.readU32(); if(got>0&&got<0x200000){
      const hx=hexdump_u8(this.b,got,4096); send2('WinHttpReadData',{size:got,hex:hx.hex,ascii:hx.ascii}); } }catch(e){}
  });
  hookExport('WINHTTP.dll','WinHttpSetOption','WinHttpSetOption',null,null);
  hookExport('WINHTTP.dll','WinHttpAddRequestHeaders','WinHttpAddRequestHeaders',function(a){ w('WinHttpAddRequestHeaders("'+esc(wideStr(a[1],2048))+'")'); });
}

// ---------- 6. 进程派生 ----------
function hookProc(){
  hookExport('KERNEL32.dll','CreateProcessW','CreateProcessW',function(a){
    w('CreateProcessW(app="'+esc(wideStr(a[0],1024))+'", cmd="'+esc(wideStr(a[1],4096))+'", flags=0x'+a[5].toInt32().toString(16)+')');
  });
  hookExport('KERNEL32.dll','CreateProcessA','CreateProcessA',function(a){
    w('CreateProcessA(app="'+esc(ansiStr(a[0],1024))+'", cmd="'+esc(ansiStr(a[1],4096))+'")');
  });
  hookExport('SHELL32.dll','ShellExecuteExW','ShellExecuteExW',function(a){
    try{ const s=a[0];
      const verb=wideStr(s.add(0*8).readPointer(),64), file=wideStr(s.add(1*8).readPointer(),1024), par=wideStr(s.add(2*8).readPointer(),4096);
      w('ShellExecuteExW(verb="'+esc(verb)+'", file="'+esc(file)+'", params="'+esc(par)+'")');
    }catch(e){ w('ShellExecuteExW(<fail>)'); }
  });
  hookExport('SHELL32.dll','ShellExecuteW','ShellExecuteW',function(a){
    w('ShellExecuteW(file="'+esc(wideStr(a[2],1024))+'", params="'+esc(wideStr(a[3],4096))+'")');
  });
  hookAny(CRT,'system','system',function(a){ w('system("'+esc(ansiStr(a[0],2048))+'")'); });
  hookExport('KERNEL32.dll','WinExec','WinExec',function(a){ w('WinExec("'+esc(ansiStr(a[0],2048))+'")'); });
  hookExport('KERNEL32.dll','OpenProcess','OpenProcess',function(a){ w('OpenProcess(access=0x'+a[0].toInt32().toString(16)+', pid='+a[2].toInt32()+')'); });
}

// ---------- 7. 注册表 / 令牌 ----------
function hookReg(){
  hookExport('ADVAPI32.dll','RegOpenKeyExW','RegOpenKeyExW',function(a){ w('RegOpenKeyExW(hive='+a[0]+', "'+esc(wideStr(a[1],512))+'")'); });
  hookExport('ADVAPI32.dll','RegCreateKeyExW','RegCreateKeyExW',function(a){ w('RegCreateKeyExW(hive='+a[0]+', "'+esc(wideStr(a[1],512))+'")'); });
  hookExport('ADVAPI32.dll','RegSetValueExW','RegSetValueExW',function(a){
    const nm=wideStr(a[1],256), ty=a[3].toInt32(), n=a[5].toInt32(); let v=null;
    if(ty===1||ty===2) v=wideStr(a[4],1024);
    else if(n>0&&n<1024){ const hx=hexdump_u8(a[4],n,512); v=hx.hex+' | '+hx.ascii; }
    send2('REGSET',{name:nm, type:ty, value:v});
  });
  hookExport('ADVAPI32.dll','GetTokenInformation','GetTokenInformation',function(a){ w('GetTokenInformation(class='+a[1].toInt32()+')'); });
  hookExport('ADVAPI32.dll','OpenProcessToken','OpenProcessToken',function(a){ w('OpenProcessToken(access=0x'+a[1].toInt32().toString(16)+')'); });
  hookExport('ADVAPI32.dll','LookupPrivilegeValueW','LookupPrivilegeValueW',function(a){ w('LookupPrivilegeValueW("'+esc(wideStr(a[1],256))+'")'); });
  hookExport('ADVAPI32.dll','AdjustTokenPrivileges','AdjustTokenPrivileges',function(){ w('AdjustTokenPrivileges'); });
}

// ---------- 8. 加密 ----------
function hookCrypto(){
  hookExport('bcrypt.dll','BCryptOpenAlgorithmProvider','BCryptOpenAlgorithmProvider',function(a){ w('BCryptOpenAlgorithmProvider("'+esc(wideStr(a[1],128))+'")'); });
  hookExport('bcrypt.dll','BCryptEncrypt','BCryptEncrypt',function(a){ send2('BCRYPTENC',{in_size:a[3].toInt32()}); });
  hookExport('bcrypt.dll','BCryptDecrypt','BCryptDecrypt',function(a){ send2('BCRYPTDEC',{in_size:a[3].toInt32()}); });
  hookExport('bcrypt.dll','BCryptGenerateSymmetricKey','BCryptGenerateSymmetricKey',function(a){ send2('BCRYPTKEY',{size:a[4].toInt32()}); });
  hookExport('bcrypt.dll','BCryptHashData','BCryptHashData',function(a){ const h=hexdump_u8(a[1],a[2].toInt32(),256); send2('BCRYPTHASH',{size:a[2].toInt32(),hex:h.hex,ascii:h.ascii}); });
  hookExport('CRYPT32.dll','CryptDecrypt','CryptDecrypt',function(){ w('CryptDecrypt'); });
  hookExport('CRYPT32.dll','CryptEncrypt','CryptEncrypt',function(){ w('CryptEncrypt'); });
  hookExport('CRYPT32.dll','CryptStringToBinaryW','CryptStringToBinaryW',function(a){ w('CryptStringToBinaryW("'+esc(wideStr(a[0],1024))+'")'); });
  hookExport('CRYPT32.dll','CryptBinaryToStringW','CryptBinaryToStringW',null,null);
  hookExport('CRYPT32.dll','CertAddEncodedCertificateToStore','CertAddEncodedCertificateToStore',function(a){ w('CertAddEncodedCertificateToStore(len='+a[2].toInt32()+')'); });
}

// ---------- 9. 反调试 ----------
function hookAnti(){
  hookExport('KERNEL32.dll','IsDebuggerPresent','IsDebuggerPresent',null,function(rv){ w('IsDebuggerPresent -> '+rv.toInt32()); });
  hookExport('KERNEL32.dll','CheckRemoteDebuggerPresent','CheckRemoteDebuggerPresent',null,null);
  hookExport('ntdll.dll','NtQueryInformationProcess','NtQueryInformationProcess',function(a){ w('NtQueryInformationProcess(class='+a[1].toInt32()+')'); });
  hookExport('KERNEL32.dll','GetComputerNameW','GetComputerNameW',function(a){ this.b=a[0]; }, function(){ w('GetComputerNameW -> "'+esc(wideStr(this.b,128))+'"'); });
  hookExport('KERNEL32.dll','GetVolumeInformationW','GetVolumeInformationW',function(a){
    this.vn=a[1]; this.sn=a[4];
  }, function(){ let sn='?'; try{ sn = this.sn.isNull()?'null':this.sn.readU32().toString(16); }catch(e){}
    w('GetVolumeInformationW(root="'+esc(wideStr(a0,16))+'" volname="'+esc(wideStr(this.vn,128))+'" serial=0x'+sn+')'); });
  hookExport('KERNEL32.dll','GlobalMemoryStatusEx','GlobalMemoryStatusEx',null,null);
  hookExport('KERNEL32.dll','GetSystemFirmwareTable','GetSystemFirmwareTable',null,null);
  hookExport('KERNEL32.dll','EnumSystemFirmwareTables','EnumSystemFirmwareTables',null,null);
  hookExport('KERNEL32.dll','GetAdaptersInfo','GetAdaptersInfo',null,null);
  hookExport('IPHLPAPI.DLL','GetAdaptersInfo','GetAdaptersInfo',null,null);
  hookExport('KERNEL32.dll','QueryPerformanceCounter','QueryPerformanceCounter',null,null);
}

// ---------- 10. MessageBox ----------
function hookUi(){
  hookExport('USER32.dll','MessageBoxW','MessageBoxW',function(a){ send2('MSGBOX',{text:wideStr(a[1],4096), caption:wideStr(a[2],512), type:a[3].toInt32()}); });
  hookExport('USER32.dll','MessageBoxA','MessageBoxA',function(a){ send2('MSGBOX',{text:ansiStr(a[1],4096), caption:ansiStr(a[2],512)}); });
  hookExport('USER32.dll','CreateWindowExW','CreateWindowExW',function(a){ w('CreateWindowExW(cls="'+esc(wideStr(a[1],128))+'", title="'+esc(wideStr(a[2],512))+'")'); });
}

// ---------- 装载 ----------
installExitGates();
hookInput();
hookConsole();
hookFiles();
hookMem();
hookNet();
hookProc();
hookReg();
hookCrypto();
hookAnti();
hookUi();

w('=== v2 loaded. HOOKED='+HOOKED.length+' FAILED='+FAILED.length);
w('HOOKED: '+HOOKED.join(', '));
if(FAILED.length) w('FAILED: '+FAILED.join(', '));
w('modules: '+Process.enumerateModules().map(function(m){return m.name;}).join(','));

// ---------- RPC ----------

// ---- 直接落盘 (exit gate 内安全调用) ----
// 修复: 不再写死 C:\alice_evoc; 依次尝试多个候选目录, 取第一个可写的
var DUMP_CANDS = [
  "C:\\alice_evoc\\dumps\\",
  "C:\\EvoFree\\dumps\\",
  (function(){ try { return Process.getCurrentDir() + "\\dumps\\"; } catch(e){ return null; } })(),
  (function(){ try { return Process.getCurrentDir() + "\\dumps\\"; } catch(e){ return null; } })()
];
var DUMPDIR = null;
function ensureDumpDir(){
  if (DUMPDIR !== null) return DUMPDIR;
  for (var i = 0; i < DUMP_CANDS.length; i++){
    var c = DUMP_CANDS[i];
    if (!c) continue;
    try {
      // Frida 没有 mkdir, 用写一个探测文件来验证可写性
      var probe = new File(c + ".alice_probe", 'wb');
      probe.write(ptr(0).readByteArray(1)); probe.close();
      DUMPDIR = c;
      w('dump dir = ' + c);
      return DUMPDIR;
    } catch(e){ /* 换下一个 */ }
  }
  // 兜底: 当前工作目录
  try { DUMPDIR = Process.getCurrentDir() + "\\"; } catch(e){ DUMPDIR = ".\\"; }
  w('dump dir fallback = ' + DUMPDIR + ' (候选都不可写, 请手动建目录)');
  return DUMPDIR;
}
function saveRange(name, addr, size){
  try {
    var d = ptr(addr).readByteArray(size);
    var dir = ensureDumpDir();
    var f = new File(dir + name, 'wb');
    f.write(d); f.close();
    return 'OK ' + size + ' -> ' + dir + name;
  } catch(e){ return 'ERR ' + e; }
}

rpc.exports = {
  saverange: function(a, l, p){
    try{ var d = ptr(a).readByteArray(l); var f = new File(p,'wb'); f.write(d); f.close(); return 'OK '+l; }catch(e){ return 'ERR '+e; }
  },
  gatedump: function(){
    var out = [];
    try {
      Process.enumerateModules().forEach(function(m){
        var nm = m.name.replace(/[^A-Za-z0-9_.-]/g, '_');
        out.push([nm, m.base.toString(), m.size, saveRange('mod_' + nm + '.bin', m.base, Math.min(m.size, 96*1024*1024))]);
      });
    } catch(e){ out.push(['enumFail', ''+e, 0, '']); }
    return out;
  },
  ctxdump: function(a, before, after){
    try{ var start = ptr(a).sub(before); var h = hexdump_u8(start, before+after, before+after); return h; }catch(e){ return {hex:'ERR '+e, ascii:''}; }
  },
  ping: function(){ return 'pong '+ts(); },
  release: function(){ RELEASED = true; return 'released'; },
  isexiting: function(){ return EXITING; },
  modules: function(){ return Process.enumerateModules().map(function(m){ return {name:m.name, base:m.base.toString(), size:m.size, path:m.path}; }); },
  ranges: function(f){ const o=[]; Process.enumerateRanges(f||'r--').forEach(function(r){ o.push({base:r.base.toString(), size:r.size, prot:r.protection, type:r.type}); }); return o; },
  readmem: function(a,l){ return hexdump_u8(ptr(a), l, l); },
  dumprange: function(a,l,p){ try{ const d=ptr(a).readByteArray(l); const f=new File(p,'wb'); f.write(d); f.close(); return 'OK '+l; }catch(e){ return 'ERR '+e; } },
  readwide: function(a,l){ try{ return ptr(a).readUtf16String(l||512); }catch(e){ return 'ERR '+e; } },
  readansi: function(a,l){ try{ return ptr(a).readAnsiString(l||512); }catch(e){ return 'ERR '+e; } },
  scan: function(pat, maxh){ const res=[]; Process.enumerateRanges('r--').forEach(function(r){ if(res.length>=(maxh||300)) return;
    try{ Memory.scanSync(r.base, r.size, pat).forEach(function(h){ if(res.length<(maxh||300)) res.push({base:r.base.toString(), addr:h.address.toString(), prot:r.protection}); }); }catch(e){} }); return res; },
  scanmod: function(mod, pat){ try{ const m=Process.getModuleByName(mod); return Memory.scanSync(m.base, m.size, pat).map(function(h){ return h.address.toString(); }); }catch(e){ return 'ERR '+e; } },
  findkey: function(key){ const res=[]; const pat = Array.prototype.map.call(key, function(c){ return ('0'+c.charCodeAt(0).toString(16)).slice(-2); }).join(' ')+' 00';
    Process.enumerateRanges('rw-').forEach(function(r){ try{ Memory.scanSync(r.base, r.size, pat).forEach(function(h){ res.push({base:r.base.toString(), addr:h.address.toString(), prot:r.protection}); }); }catch(e){} }); return res; }
};
