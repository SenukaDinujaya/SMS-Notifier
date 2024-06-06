function disablePage() {
    var overlay = document.createElement("div");
    overlay.className = "overlay";
    
    var spinner = document.createElement("div");
    spinner.className = "spinner";
    overlay.appendChild(spinner);
    
    document.body.appendChild(overlay);
  }
  
  document.addEventListener("DOMContentLoaded", function () {
    var runButtons = document.querySelectorAll("button[data-action='run']");
    var stopButtons = document.querySelectorAll("button[data-action='stop']");
    
    runButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        disablePage();
      });
    });
    
    stopButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        disablePage();
      });
    });
  });
  