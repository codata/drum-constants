const { response } = require('express')
const express = require('express')
const codataConstants = require('./codata_constants.json')
const router = express.Router()

// middleware that is specific to this router
router.use((req, res, next) => {
    console.log('Time: ', Date.now())
    next()
})
// define the home page route
router.get('/', (req, res) => {
    res.send('API home page')
})


router.get('/Constant/:id', (req, res) => {
    let id = req.params.id
    let resource = getConstant(id)
    if (resource) {
        res.json(resource)
    }
    else {
        res.status(404).send('Resource not found')
    }
})

router.get('/ConstantInstance/:id', (req, res) => {
    let id = req.params.id
    let resource = getConstantInstance(id)
    if (resource) {
        res.json(resource)
    }
    else {
        res.status(404).send('Resource not found')
    }
})

router.get('/search', (req, res) => {
    let name = 'name' in req.query ? req.query.name : '';
    let filter = { "name": name }
    let matches = findByName(name)
    let nMatches = matches.length
    // paginate
    let page = 'page' in req.query ? parseInt(req.query.page) : 1;
    let perPage = 'perPage' in req.query ? parseInt(req.query.perPage) : 20;
    let nPages = nMatches > 0 ? Math.floor(nMatches / perPage)+1 : 0
    matches = matches.slice(perPage * (page - 1), perPage * (page - 1) + perPage)
    // prepare response
    let response = { filter: filter, found: nMatches, page: page, perPage: perPage, nPages: nPages, matches: formatMatches(matches, req) }
    response.matches = matches
    // return
    res.json(response)
})

module.exports = router

function getConstant(id) {
    let match = null
    for (constant of codataConstants.constants) {
        if (id == constant.id) {
            match = constant
        }
    }
    return match
}

function getConstantInstance(id) {
    let match = null
    for (constant of codataConstants.constants) {
        for (instance of constant.instances) {
            if (id == instance.id) {
                match = instance
            }
        }
    }
    return match
}

function findByName(name) {
    let matches = []
    const re = new RegExp(name, "ig");
    for (constant of codataConstants.constants) {
        for (instance of constant.instances) {
            if (re.test(instance.versions[0].name_en)) {
                matches.push(instance)
            }
        }
    }
    return matches
}


function formatMatches(matches, req) {
    return matches
}

function regExpEscape(literal_string) {
    return literal_string.replace(/[-[\]{}()*+!<=:?.\/\\^$|#\s,]/g, '\\$&');
}