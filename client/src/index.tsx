import React from 'react';
import { render } from 'react-dom';
import { BrowserRouter } from 'react-router-dom';

import App from './App';

import * as serviceWorker from './serviceWorker';

import { MuiThemeProvider, createTheme } from '@material-ui/core/styles';

import CssBaseline from '@material-ui/core/CssBaseline';
import 'react-bootstrap-table-nextgen/dist/react-bootstrap-table-nextgen.min.css';

import './styles/index.scss';

const darkTheme = createTheme({
  // settings for Material UI components
  palette: {
    type: 'dark',
    primary: {
      light: '#C0D9E5',
      main: '#668DA2',
      dark: '#244454',
      contrastText: '#fff',
    },
    secondary: {
      light: 'rgba(255, 132, 141, 1)',
      main: 'rgba(235, 81, 96, 1)',
      dark: 'rgba(179, 20, 54, 1)',
      contrastText: '#fff',
    },
  },
  typography: {
    fontFamily: 'Roboto, Arial',
  },
});

render(
  <BrowserRouter>
    <MuiThemeProvider theme={darkTheme}>
      <CssBaseline />
      <App />
    </MuiThemeProvider>
  </BrowserRouter>,
  document.getElementById('root')
);

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
