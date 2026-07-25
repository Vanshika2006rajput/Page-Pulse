async function audit(){

let url=document.getElementById("url").value.trim();

let result=document.getElementById("result");
let loading=document.getElementById("loading");

if(url===""){
result.innerHTML="<h3 style='color:red'>Please enter a website URL.</h3>";
return;
}

loading.style.display="block";
result.innerHTML="";

try{

let response=await fetch("/audit",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({url:url})
});

let data=await response.json();

loading.style.display="none";

if(data.error){
result.innerHTML="<h3 style='color:red'>"+data.error+"</h3>";
return;
}

let color="green";

if(data.status>=400){
color="red";
}
else if(data.status>=300){
color="orange";
}

result.innerHTML=`
<div class="card">
<h3>Status</h3>
<p class="${color}">${data.status}</p>
</div>

<div class="card">
<h3>Response Time</h3>
<p>${data.responseTime}</p>
</div>

<div class="card">
<h3>Title</h3>
<p>${data.title}</p>
</div>

<div class="card">
<h3>Description</h3>
<p>${data.description}</p>
</div>

<div class="card">
<h3>Word Count</h3>
<p>${data.wordCount}</p>
</div>

<div class="card">
<h3>Images Missing Alt</h3>
<p>${data.imagesWithoutAlt}</p>
</div>
`;

}
catch(err){
loading.style.display="none";
result.innerHTML="<h3 style='color:red'>Something went wrong.</h3>";
}

}