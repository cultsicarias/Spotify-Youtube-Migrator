// static/app.js
async function openSpotifyLogin(){
  window.open('/auth/spotify/login', '_blank');
}

async function uploadHeaders(){
  const f = document.getElementById('file-input').files[0];
  if(!f){ alert('Pick browser.json'); return; }
  const fd = new FormData();
  fd.append('file', f);
  document.getElementById('upload-status').innerText = 'Uploading...';
  const res = await fetch('/youtube/auth/upload', { method: 'POST', body: fd });
  if(res.ok){ document.getElementById('upload-status').innerText = 'Uploaded'; }
  else { document.getElementById('upload-status').innerText = 'Upload failed'; }
}

async function loadPlaylists(){
  document.getElementById('refresh-playlists').innerText = 'Loading...';
  const res = await fetch('/spotify/playlists');
  if(!res.ok){ alert('Load playlists failed. Login first.'); document.getElementById('refresh-playlists').innerText = 'Load My Playlists'; return; }
  const data = await res.json();
  const sel = document.getElementById('playlist-select');
  sel.innerHTML = '';
  for(const it of data.get('items', [])){
    const opt = document.createElement('option');
    opt.value = it.id;
    opt.text = `${it.name} (${it.tracks.total})`;
    sel.appendChild(opt);
  }
  document.getElementById('refresh-playlists').innerText = 'Load My Playlists';
}

async function transfer(){
  const sel = document.getElementById('playlist-select');
  if(!sel.value){ alert('Pick playlist'); return; }
  document.getElementById('transfer-status').innerText = 'Transferring...';
  const res = await fetch(`/transfer?spotify_playlist_id=${sel.value}`, { method: 'POST' });
  const data = await res.json();
  document.getElementById('transfer-status').innerText = 'Done';
  document.getElementById('report').innerText = JSON.stringify(data, null, 2);
}

document.getElementById('spotify-login').onclick = openSpotifyLogin;
document.getElementById('upload-headers').onclick = uploadHeaders;
document.getElementById('refresh-playlists').onclick = loadPlaylists;
document.getElementById('transfer-btn').onclick = transfer;
