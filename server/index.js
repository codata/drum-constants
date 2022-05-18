const express = require("express");
const path = require("path");
const sls = require('serverless-http')
var app = express();

app.use('/images', express.static(path.join(__dirname, 'images')))
app.use('/js', express.static(path.join(__dirname, 'js')))

app.listen(3000, () => {
    console.log("Server running on port 3000");
});

// define the home page route
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '/home.html'))
 })

const api = require('./api')
app.use('/api', api)

module.exports.server = sls(app)