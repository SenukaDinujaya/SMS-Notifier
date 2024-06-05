document.getElementById('runButton').addEventListener('click', function() {
    var spinnerContainer = document.getElementById('spinnerContainer');
    
    // Remove existing spinner if any
    spinnerContainer.innerHTML = '';

    // Create the spinner div
    var spinner = document.createElement('div');
    spinner.className = 'spinner';

    // Add the spinner to the container
    spinnerContainer.appendChild(spinner);
});
