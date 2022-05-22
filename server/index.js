const express = require("express");
const path = require("path");
const sls = require('serverless-http')
var app = express();

app.use('/public', express.static(path.join(__dirname, 'public')))

app.listen(3000, () => {
    console.log("Server running on port 3000");
});

// Root
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '/home.html'))
 })

 // api
const api = require('./api')
app.use('/api', api)

module.exports.server = sls(app)