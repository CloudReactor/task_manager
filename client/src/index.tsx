import React from 'react';
import { createRoot } from 'react-dom/client';

import {
  createBrowserRouter,
  RouterProvider
} from 'react-router-dom';

import App from './App';

import * as serviceWorker from './serviceWorker';

import { ThemeProvider, Theme, StyledEngineProvider, createTheme, adaptV4Theme } from '@mui/material/styles';

import CssBaseline from '@mui/material/CssBaseline';
import 'react-bootstrap-table-next-react18-node20/dist/react-bootstrap-table2.min.css';

import './styles/index.scss';


declare module '@mui/styles/defaultTheme' {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  interface DefaultTheme extends Theme {}
}


const darkTheme = createTheme(adaptV4Theme({
  // settings for Material UI components
  palette: {
    mode: 'dark',
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
}));

const router = createBrowserRouter([
  {
    path: "*",
    element: (
      <StyledEngineProvider injectFirst>
        (<ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <App />
        </ThemeProvider>)
      </StyledEngineProvider>
    )
  }
]);

const container = document.getElementById('root');
const root = createRoot(container!);

root.render(
  <RouterProvider router={router} />,
);

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
