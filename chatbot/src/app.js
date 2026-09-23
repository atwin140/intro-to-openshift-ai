const form=document.querySelector('#chat'), input=document.querySelector('#prompt'), list=document.querySelector('#messages'), send=document.querySelector('#send'), status=document.querySelector('#status');
let history=[], busy=false;
function bubble(role,text,source='') {
  document.querySelector('#welcome')?.remove();
  const article=document.createElement('article'); article.className=role;
  const label=document.createElement('div'); label.className='label'; label.textContent=role==='user'?'You':source||'Lab assistant'; article.append(label);
  const parts=text.split(/```[^\n]*\n([\s\S]*?)```/g);
  parts.forEach((part,i)=>{if(!part)return; if(i%2){const box=document.createElement('div');box.className='codebox';const pre=document.createElement('pre'), code=document.createElement('code'),copy=document.createElement('button');code.textContent=part.trim();pre.append(code);copy.textContent='Copy';copy.className='copy';copy.onclick=async()=>{try{await navigator.clipboard.writeText(code.textContent);copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy',1500)}catch{copy.textContent='Select to copy'}};box.append(copy,pre);article.append(box)}else{const p=document.createElement('p');part.trim().split(/(\*\*[^*]+\*\*|`[^`]+`)/g).forEach(t=>{if(t.startsWith('**')&&t.endsWith('**')){const strong=document.createElement('strong');strong.textContent=t.slice(2,-2);p.append(strong)}else if(t.startsWith('`')&&t.endsWith('`')){const code=document.createElement('code');code.textContent=t.slice(1,-1);p.append(code)}else p.append(document.createTextNode(t))});article.append(p)}});
  list.append(article); article.scrollIntoView({behavior:'smooth',block:'end'});return article;
}
form.addEventListener('submit',async e=>{
  e.preventDefault();if(busy||!input.value.trim())return;
  const text=input.value.trim(); let request=[...history.slice(-40),{role:'user',content:text}];
  let locallyTrimmed=Math.max(0,history.length-40);while(request.length>1&&request.reduce((n,m)=>n+m.content.length,0)>96000){request.splice(0,2);locallyTrimmed+=2;}
  bubble('user',text);input.value='';busy=true;send.disabled=true;document.querySelector('#reset').disabled=true;status.textContent='Thinking…';
  try{const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:request}),signal:AbortSignal.timeout(135000)});const data=await response.json();if(!response.ok)throw Error(data.error||'Unable to send message.');bubble('assistant',data.answer,data.source);history=[...request.slice(data.trimmed_messages||0),{role:'assistant',content:data.answer}];status.textContent=data.usage?`${data.usage.prompt_tokens} input + ${data.usage.completion_tokens} output tokens · ${data.seconds}s${data.trimmed_messages||locallyTrimmed?' · Older exchanges removed to fit':''}${data.finish_reason==='length'?' · Reply limit reached':''}`:'Ready for your next question';}
  catch(error){bubble('assistant',error.name==='TimeoutError'?'The request timed out. Please try again.':error.message,'Request could not complete');input.value=text;status.textContent='Please try again';}
  finally{busy=false;send.disabled=false;document.querySelector('#reset').disabled=false;input.focus();}
});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();form.requestSubmit();}});
document.querySelectorAll('.suggestions button').forEach(b=>b.onclick=()=>{input.value=b.textContent;form.requestSubmit()});
document.querySelector('#reset').onclick=()=>{if(!busy){history=[];list.replaceChildren();input.value='';status.textContent='New chat started';input.focus();}};
