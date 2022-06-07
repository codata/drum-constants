
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
        resetPage()
        search()
    })
});

function resetPage() {
    let pageSelect = document.getElementById('search-page-select')
    if(pageSelect) pageSelect.value = 1
}

function search() {
    let name = document.getElementById('search-input').value
    let pageSelect = document.getElementById('search-page-select')
    let page = pageSelect ? pageSelect.value : 1
    let url = "api/search?name=" + name + "&page=" + page
    document.getElementById('search-api-url').setAttribute('href', url)
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    // API async
    xhr.onload = function () {
        if (this.status === 200) {
            let results = JSON.parse(this.responseText);
            renderSearch(results);
        }
        else {
            console.log(this.status);
        }
    }
    // call API
    xhr.send();
}


function renderAbout(data) {
    let resultsContainer = document.getElementById('search-results')
    let html = ""
    html += "<div class='w-75 m-auto'>"
    html += "<h2 class='w-25'>About</h2>"
    html += "<p>"
    html += "This prototype website and API provides access in machine actionable formats to information on Fundamental Physical Constants."
    html += " This includes the constants' names, values, uncertainty (including changes over time), units, and unique identifiers."    
    html += "</p>"
    html += "<p>"
    html += "The underlying information has been collected from the <a href='https://physics.nist.gov/cuu/Constants/index.html' target='_blank'>U.S. National Institute of Technology (NIST)</a> website and other sources, and used to generate the documentation in JSON format to drive the API."
    html += "</p>"
    html += "<p>"
    html += "This project is taking place under the the umbrella of CODATA <a href='https://codata.org/initiatives/task-groups/drum/' target='_blank'>Digital Representation of Units of Measurement (DRUM)</a> task group."
    html += " Note that the is work in progress, and should only be used for evaluation, development, or educational purposes."
    html += "</p>"   
    html += "<p>"
    html += "For more information or to feedback/contribute, please visit our <a href='https://github.com/codata/drum-constants' target='_blank'>GitHub project site</a>"
    html += "</p>"
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
    let html = "<div>"
    html += "@TODO"
    html += "</div>"
    return html
}

function renderConstantVersion(data) {
    let html = "<div>"
    html += "@TODO"
    html += "</div>"
    return html
}

function renderSearch(results) {
    let resultsContainer = document.getElementById('search-results')
    let matches = results.matches
    // render
    let html = "<div>"
    if (matches.length == 0) {
        html += "No matches"
    }
    else {
        // Search Header
        html += "<div class='row'>" 
        html += "<div class='col'>Found "+results.found + " matches</div>"
        // Page selector
        html += "<div class='col'>"
        html += '<div class="row g-3 float-end">'
            html += '<label for="search-page-select" class="col-auto">Page </label>'
            html += '<div class="col-auto">'
            html += '<select id="search-page-select" class="form-select form-select-sm" style="width:auto;" onchange="search()">'
            for(let i=1; i <= results.nPages; i++) {
                html += '<option value="'+i+'"'+(i==results.page ? ' selected="selected"' : '')+'>'+i+'</option>'
            }
            html += '</select>'
            html += '</div>'
            html += '<div class="col-auto"> of '+results.nPages+'</div>'
        html += '</div>' // end page selector
        html += "</div>" // end search header
        // Results
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
            html += "<td>" + latest.name 
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
            let uncertainty = latest.uncertainty ? latest.uncertainty : "-" 
            html += "<td>" + uncertainty + "</td>"
            // version
            html += "<td data-bs-toggle='tooltip' data-html='true' title='"+tooltip+"'>" + latest.version + "</td>"
            html += "</tr>"
        }
        html += "</tbody>"
        html += "</table>"
        html += "</div>" // end results container
        // Search footer
        html += '<div class="row mb-3">'
            html += '<div class="col-1 text-start">'
            html += '<button class="btn btn-sm btn-primary"'+(results.page == 1 ? ' disabled' : '')+' onclick="getElementById(\'search-page-select\').value = '+(results.page-1)+';search();"><< Prev</button>'
            html += '</div>'
            html += '<div class="col text-center">'
            for(let i=1; i <= results.nPages; i++) {
                html += '<button class="btn btn-sm btn-light"'+(results.page == i ? ' disabled' : '')+' onclick="getElementById(\'search-page-select\').value = '+i+';search();">'+i+'</button>'
            }
            html += '</div>'
            html += '<div class="col-1 text-end">'
            html += '<button class="btn btn-sm btn-primary"'+(results.page >= results.nPages ? ' disabled' : '')+' onclick="getElementById(\'search-page-select\').value = '+(results.page+1)+';search();">>> Next</button>'
            html += '</div>'
        html += '</div>' // end search footer
    }
    html += "</div>"
    resultsContainer.innerHTML = html
}