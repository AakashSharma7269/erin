//imports
import express from "express";
import path from "path";
import dotenv from "dotenv";
import expresshandlebars  from 'express-handlebars';

//importing the website routes into const's
const indexPage:express.Router = require('./routes/index');
const formPage:express.Router = require('./routes/formpage');

//api endpoint imports
const updateEndpoint:express.Router = require('./routes/api/update');
const fetchEndpoint:express.Router = require('./routes/api/fetch');
const apiIndexPage:express.Router =  require('./routes/api/index')

//project config
dotenv.config({"path":path.join(__dirname,"../../.env")});                  //dotenv config
const app:express.Application = express();                                  //express app const
const port = process.env.SERVER_PORT || 80;                                 //express port constant 

//initializing the express app 
app.engine('handlebars',expresshandlebars({defaultLayout:'homepage'}));     //Handlebars middleware
app.set('view engine','handlebars');                                        // setting the view engine aka the template renderer
app.set( "views", path.join( __dirname, "./views" ) );                      // overwriting the default view folder path
app.use(express.static(path.join(__dirname + "./../dist/assets")));         //setting the assets folder as static so the handlebar files can import the css and js as needed
app.use(express.json());                                                    //converts it to json using the default express body-parser
app.use(express.urlencoded({ extended: false }));                           //bodyparser middleware

//setting up the website routes
app.use('/',indexPage);
app.use('/dashboard',formPage);

//setting up the api routes
app.use('/api/v1',apiIndexPage)
app.use('/api/v1/fetch',fetchEndpoint);
app.use('/api/v1/update',updateEndpoint);

//setting up 404 page
app.use(function(req:express.Request,res:express.Response,next:express.NextFunction){
    res.status(404)
    // respond with html page
    if (req.accepts('html')) {
        res.status(400).render('NotFound')
        return;
    }

    // respond with json
    if (req.accepts('json')) {
        res.json({ error: 'Not found' });
        return;
    }

    // default to plain-text. send()
    res.type('txt').send('Not found');
});

//Running the files
app.listen( port, () => console.log( `Server started at http://localhost:${ port }`));