
var blinkWarning = document.getElementById("myNavbar");

ws = new WebSocket("ws://"+window.location.hostname .toString()+":3002/postgresql2websocket");

ws.onopen = function(e) {
  console.log("[open] Connection established");
};

ws.onmessage = function (message) {
  var text = (new Date).toLocaleString() + ': ' + message.data;
  let nuevoRegistro = JSON.parse(message.data);

  if (nuevoRegistro.table === "forecast_warning") {
       
        if (nuevoRegistro.row.active === true) {
            blinkWarning.innerHTML  = 'NUEVO AVISO: '+ nuevoRegistro.row.text +'. Pulsa <a href="/avisos">aquí</a> para obtener más información.'
            blinkWarning.style.visibility = "visible";
        } else {
            //blinkWarning.style.visibility = "hidden";
        }
  }
}


ws.onclose = function(event) {
  if (event.wasClean) {
    console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
  } else {
    // e.g. server process killed or network down
    // event.code is usually 1006 in this case
    console.log('[close] Connection died');
  }
};

ws.onerror = function(error) {
  console.log(`[error] ${error.message}`);
};
