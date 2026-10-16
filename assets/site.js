/* Spicewood Living — shared page script */
(function(){
const $=s=>document.querySelector(s);

/* old #links (e.g. from emails) → real pages */
const OLD={week:"this-week.html",directory:"local-businesses.html",moving:"moving-to-spicewood.html",advertise:"advertise.html",newsletter:"newsletter.html"};
const h=(location.hash||"").slice(1);
if(OLD[h]&&document.body.dataset.page==="home"){location.replace(OLD[h]);return}

/* phone menu: scroll the current page's link into view */
const nav=$("nav.links"),cur=nav&&nav.querySelector('[aria-current="page"]');
if(cur&&nav.scrollWidth>nav.clientWidth)nav.scrollLeft=(cur.offsetLeft-nav.offsetLeft)-(nav.clientWidth-cur.offsetWidth)/2;

/* events: hide ones that have already happened (only on the current week's page) */
const ev=$("#events");
if(ev&&ev.dataset.live==="1"){
  const today=new Date();today.setHours(0,0,0,0);let shown=0;
  ev.querySelectorAll("li[data-date]").forEach(li=>{const past=new Date(li.dataset.date+"T23:59:00")<today;li.hidden=past;if(!past)shown++});
  if(!shown&&$("#noEvents"))$("#noEvents").hidden=false;
}

/* local businesses: search + category filter */
const list=$("#listings");
if(list){
  let cat="All";const q=$("#q");
  function apply(){
    const term=(q.value||"").trim().toLowerCase();let n=0;
    list.querySelectorAll(".biz").forEach(b=>{const ok=(cat==="All"||b.dataset.cat===cat)&&(!term||b.textContent.toLowerCase().includes(term));b.hidden=!ok;if(ok)n++});
    $("#noMatch").hidden=n>0;
  }
  $("#chips").addEventListener("click",e=>{const c=e.target.closest(".chip");if(!c)return;cat=c.dataset.c;
    document.querySelectorAll("#chips .chip").forEach(x=>x.setAttribute("aria-pressed",String(x===c)));apply()});
  q.addEventListener("input",apply);
}

function show(el,cls,msg){el.className="status "+cls;el.textContent=msg;el.hidden=false}

/* business listing requests → emailed via FormSubmit */
const FORM_ENDPOINT="https://formsubmit.co/ajax/info@spicewoodtxliving.com";
async function send(subject,data,statusEl){
  try{
    const r=await fetch(FORM_ENDPOINT,{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},body:JSON.stringify({_subject:subject,_template:"table",_captcha:"false",...data})});
    if(!r.ok)throw new Error(r.status);return true;
  }catch{show(statusEl,"alt","That didn't go through. Please try again, or text Madison at (830) 613-7999.");return false}
}

/* newsletter → Mailchimp (audience: Spicewood Living Weekly) */
const MC_URL="https://spicewoodtxliving.us6.list-manage.com/subscribe/post-json?u=c85341195b7c7b6c0ab00bdd8&id=11bad09d16&f_id=00fac2e1f0";
const MC_BOT="b_c85341195b7c7b6c0ab00bdd8_11bad09d16";
function mcSubscribe(fields){
  return new Promise((resolve,reject)=>{
    const cb="mc_cb_"+Date.now(),sc=document.createElement("script");
    const q=Object.entries({...fields,[MC_BOT]:""}).map(([k,v])=>encodeURIComponent(k)+"="+encodeURIComponent(v)).join("&");
    const t=setTimeout(()=>{cleanup();reject(new Error("timeout"))},12000);
    function cleanup(){clearTimeout(t);delete window[cb];sc.remove()}
    window[cb]=r=>{cleanup();resolve(r)};
    sc.src=MC_URL+"&"+q+"&c="+cb;sc.onerror=()=>{cleanup();reject(new Error("network"))};
    document.body.appendChild(sc);
  });
}
function wireNewsletter(form,ids,onDone){
  const g=id=>form.querySelector("#"+id);
  form.addEventListener("submit",async e=>{e.preventDefault();
    const email=g(ids.email).value.trim(),first=g(ids.first).value.trim(),last=g(ids.last).value.trim(),st=g(ids.status),btn=form.querySelector("button[type=submit]");
    if(!first||!last){show(st,"alt","Add your first and last name.");return}
    if(!/^\S+@\S+\.\S+$/.test(email)){show(st,"alt","Enter a valid email address so we can send the Monday email.");return}
    btn.disabled=true;
    try{
      const r=await mcSubscribe({EMAIL:email,FNAME:first,LNAME:last});
      if(r.result==="success"){show(st,"ok","You're subscribed. Look for This Week in Spicewood on Monday.");form.reset();onDone&&onDone()}
      else if(/already subscribed/i.test(r.msg||"")){show(st,"ok","You're already on the list. See you Monday.");onDone&&onDone()}
      else{show(st,"alt","That didn't go through. Check your email address and try again.")}
    }catch{show(st,"alt","That didn't go through. Please try again, or text Madison at (830) 613-7999.")}
    finally{btn.disabled=false}
  });
}
const nl=$("#nlForm");
if(nl)wireNewsletter(nl,{first:"n_first",last:"n_last",email:"n_email",status:"nlStatus"},()=>remember("nl_subscribed","1"));

/* newsletter popup: a few seconds after the page opens; closing hides it for the rest of the visit */
function recall(k){try{return localStorage.getItem(k)}catch{return null}}
function remember(k,v){try{localStorage.setItem(k,v)}catch{}}
const POP_DELAY=6000;
function recallVisit(k){try{return sessionStorage.getItem(k)}catch{return null}}
function rememberVisit(k,v){try{sessionStorage.setItem(k,v)}catch{}}
(function(){
  if(document.body.dataset.page==="newsletter"||recall("nl_subscribed"))return;
  if(recallVisit("nl_popup_closed"))return; /* closed this visit: show again next visit */
  const wrap=document.createElement("div");wrap.className="nl-pop";wrap.hidden=true;
  wrap.innerHTML=`<div class="nl-pop-card" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="popTitle">
    <button type="button" class="nl-pop-x" aria-label="Close">&times;</button>
    <span class="label">The weekly email</span>
    <h2 id="popTitle">This Week in Spicewood, every Monday</h2>
    <p>New openings, the weekend's live music, and what's happening around town. Short, local, and free.</p>
    <form id="popForm" novalidate>
      <div class="row2">
        <label class="f">First name<input id="p_first" autocomplete="given-name" required></label>
        <label class="f">Last name<input id="p_last" autocomplete="family-name" required></label>
      </div>
      <label class="f">Email<input id="p_email" type="email" autocomplete="email" required></label>
      <button class="go" type="submit">Subscribe</button>
      <div id="popStatus" class="status" hidden></div>
    </form>
    <button type="button" class="nl-pop-no">No thanks</button>
  </div>`;
  document.body.appendChild(wrap);
  let lastFocus=null;
  function close(){wrap.hidden=true;document.removeEventListener("keydown",onKey);rememberVisit("nl_popup_closed","1");lastFocus&&lastFocus.focus&&lastFocus.focus()}
  function onKey(e){if(e.key==="Escape")close()}
  wrap.addEventListener("click",e=>{if(e.target===wrap||e.target.closest(".nl-pop-x,.nl-pop-no"))close()});
  wireNewsletter(wrap.querySelector("#popForm"),{first:"p_first",last:"p_last",email:"p_email",status:"popStatus"},()=>{remember("nl_subscribed","1");setTimeout(close,2500)});
  setTimeout(()=>{lastFocus=document.activeElement;wrap.hidden=false;document.addEventListener("keydown",onKey);wrap.querySelector(".nl-pop-card").focus({preventScroll:true})},POP_DELAY);
})();

const biz=$("#bizForm");
if(biz)biz.addEventListener("submit",async e=>{e.preventDefault();
  const st=$("#bizStatus"),name=$("#b_name").value.trim(),first=$("#b_first").value.trim(),last=$("#b_last").value.trim(),email=$("#b_email").value.trim();
  if(!name||!first||!last){show(st,"alt","Add your business name and your first and last name.");return}
  if(!/^\S+@\S+\.\S+$/.test(email)){show(st,"alt","Enter a valid email address so Madison can reach you.");return}
  if(await send("Listing request: "+name,{business:name,category:$("#b_cat").value,first_name:first,last_name:last,email,phone:$("#b_phone").value.trim(),tier:$("#b_tier").value,address:$("#b_addr").value.trim(),description:$("#b_desc").value.trim()},st)){
    show(st,"ok","Request received. Madison will follow up within two business days.");biz.reset()}
});
})();
