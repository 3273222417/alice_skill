'use strict';
// evo_free.js -- Evo 免卡密内存补丁 agent
// 作用: 让订阅 / 授权校验通过, 进入功能界面 (无需卡密)
// 原理: 响应解析结构体 Authorization+0xC0 的三个时间字段 (激活/过期/服务器时间)
//       由服务端响应决定; 若服务端未提供, 此处直接写入合法时间戳.
//       判定链:
//         sub { +0x40 激活, +0x48 过期, +0xe8 服务器时间 }  要求 激活 < 服务器时间 < 过期
//         auth { +0x100 激活, +0x108 过期, +0x1a8 服务器时间 } 要求 服务器时间 < 过期
var EVO = null, N = 0, LIFE = 3650 * 86400, UC = 0;
function base() {
  if (EVO === null) {
    var ms = Process.enumerateModules();
    for (var i = 0; i < ms.length; i++) if (ms[i].name.toLowerCase() === "evo.exe") { EVO = ms[i].base; break; }
    if (EVO === null) for (var j = 0; j < ms.length; j++)
      if (ms[j].path && ms[j].path.toLowerCase().indexOf("evo.exe") >= 0) { EVO = ms[j].base; break; }
  }
  return EVO;
}
function now() { return Math.floor(Date.now() / 1000); }
function el(s) { if (N < 400) { N++; send(s); } }
function stampSub(p, tag) {
  var t = now();
  p.add(0x40).writePointer(ptr(t - 3600));   // activation < now
  p.add(0x48).writePointer(ptr(t + LIFE));   // expiration > now
  p.add(0xe8).writePointer(ptr(t));          // server time = now
  el(tag + " sub stamped act=" + (t - 3600) + " exp=" + (t + LIFE) + " srv=" + t);
}
function fixAuth(t, tag) {
  var tt = now();
  t.add(0x180).writePointer(ptr(200));       // HTTP 200
  t.add(0x1b0).writeU8(1);                   // has response
  t.add(0x100).writePointer(ptr(tt - 3600));
  t.add(0x108).writePointer(ptr(tt + LIFE));
  t.add(0x1a8).writePointer(ptr(tt));
  el(tag + " auth stamped");
}
setImmediate(function () {
  var b = base();
  send("evo_free agent attached. base=" + b);
  try { Interceptor.attach(b.add(0x1469B0), {   // fetch subscription
      onEnter: function (a) { this.dst = a[1]; },
      onLeave: function () { stampSub(this.dst, "fetch"); }
    }); } catch (e) { send("fetch hook FAIL " + e); }
  try { Interceptor.attach(b.add(0x144DA0), {   // apply response -> Authorization+0xC0
      onEnter: function (a) { this.d = a[0]; },
      onLeave: function () { stampSub(this.d, "apply"); }
    }); } catch (e) { send("apply hook FAIL " + e); }
  try { Interceptor.attach(b.add(0x1480A0), {   // isValid
      onEnter: function (a) { stampSub(a[1], "isvalid"); },
      onLeave: function (r) { r.replace(ptr(1)); }
    }); } catch (e) { send("isvalid hook FAIL " + e); }
  try { Interceptor.attach(b.add(0x144FC0), {   // validate + log
      onEnter: function (a) { fixAuth(a[0], "validate"); }
    }); } catch (e) { send("validate hook FAIL " + e); }
  try { Interceptor.attach(b.add(0x177EDC), {   // UI state machine (per frame)
      onEnter: function () { UC++; if (UC % 600 === 0) fixAuth(this.context.rsi, "ui"); }
    }); } catch (e) { send("ui hook FAIL " + e); }
  send("hooks installed");
});
