
window.addEventListener('load', (event) => {
    let searchInput = document.getElementById('search-input')
    let searchButton = document.getElementById('search-button')
    searchInput.addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            searchButton.click();
        }
    })
    searchButton.addEventListener("click", function (event) {
        search()
    })
});

function search() {
    let value = document.getElementById('search-input').value
    let url = "api/search?name=" + value
    document.getElementById('search-api-url').setAttribute('href', url)
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    // API async
    xhr.onload = function () {
        console.log(this.status);
        if (this.status === 200) {
            let results = JSON.parse(this.responseText);
            console.log(results);
            renderSearch(results);
        }
        else {
            console.log(this.status);
        }
    }
    // call API
    xhr.send();
}

function renderSearch(results) {
    resultsContainer = document.getElementById('search-results')
    let matches = results.matches
    // render
    let html = "<div>"
    if (matches.length == 0) {
        html += "No matches"
    }
    else {
        html += "<div>" + results.found + " matches" + "</div>"
        html + "<div class='container'>"
        html += "<table class='table table-striped'>"
        html += "<thead>"
        html += "<tr>"
        html += "<th>Name</th>"
        html += "<th>Units</th>"
        html += "<th>Value</th>"
        html += "<th>Uncertainty</th>"
        html += "<th>Version</th>"
        html += "</tr>"
        html += "</thead>"
        html += "<tbody>"
        for (const data of matches) {
            let unitsSI = 'SI' in data.units ? data.units['SI'] : ''
            let latest = data.versions[0]
            let tooltip = ''
            for(version of data.versions) {
                tooltip += version.version+': '+version.value+' &#xb1;'+version.uncertainty+'&#013;'
            }
            html += "<tr class='text-start'>"
            // name
            html += "<td>" + latest.name_en 
            html += "&nbsp;<a href='api/ConstantInstance/"+data.id+"' target='_blank'><i class='bi bi-filetype-json'></i></a>"
            html += "</td>"
            // units
            html += "<td>"
            if('UOM' in data.units) {
                html += "<a href='"+data.units.UOM+"' target='_blank'>"+unitsSI+"</a>"
            }
            else {
                html += unitsSI 
            }
            html += "</td>"
            // value
            html += "<td>" + latest.value 
            
            html += '<button type="button" class="btn btn-light btn-sm"><i class="bi bi-clipboard" onclick="navigator.clipboard.writeText(\''+latest.value+'\')"></i></button>'
            html += "</td>"
            // uncertainty
            html += "<td>" + latest.uncertainty + "</td>"
            // version
            html += "<td data-bs-toggle='tooltip' data-html='true' title='"+tooltip+"'>" + latest.version + "</td>"
            html += "</tr>"
        }
        html += "</tbody>"
        html += "</table>"
        html += "</div>"
    }
    html += "</div>"
    resultsContainer.innerHTML = html
}

function renderConstant(data) {
    let html = "<div>"
    html += "@TODO"
    html += "</div>"
    return html
}

function renderConstantInstance(data) {
    let html = ""
    return html
}

function renderConstantValue(data) {
    let html = "<div>"
    html += "@TODO"
    html += "</div>"
    return html
}
