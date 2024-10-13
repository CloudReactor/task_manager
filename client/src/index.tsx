import * as React from 'react';
import { createRoot } from 'react-dom/client';

import {
  createBrowserRouter,
  RouterProvider
} from 'react-router-dom';

import App from './App';

import * as serviceWorker from './serviceWorker';

import { ThemeProvider, StyledEngineProvider, createTheme, alpha } from '@mui/material/styles';
import { grey } from "@mui/material/colors";

import CssBaseline from '@mui/material/CssBaseline';
import 'react-bootstrap-table-next-react18-node20/dist/react-bootstrap-table2.min.css';

import './styles/index.scss';

// Restore "default" color for MUI Buttons, from:
// https://codesandbox.io/p/sandbox/mimic-v4-button-default-color-bklx8?file=%2Fsrc%2FDemo.tsx%3A35%2C9-80%2C12

declare module "@mui/material/Button" {
  interface ButtonPropsColorOverrides {
    grey: true;
  }
}

declare module "@mui/material" {
  interface Color {
    main: string;
    dark: string;
  }
}

const theme = createTheme({
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
    grey: {
      main: grey[300],
      dark: grey[400]
    }
  },
  typography: {
    fontFamily: 'Roboto, Arial',
  },
});

const darkTheme = createTheme(theme, {
  components: {
    MuiButton: {
      variants: [
        {
          props: { variant: "contained", color: "grey" },
          style: {
            color: theme.palette.getContrastText(theme.palette.grey[300])
          }
        },
        {
          props: { variant: "outlined", color: "grey" },
          style: {
            color: theme.palette.text.primary,
            borderColor:
              theme.palette.mode === "light"
                ? "rgba(0, 0, 0, 0.23)"
                : "rgba(255, 255, 255, 0.23)",
            "&.Mui-disabled": {
              border: `1px solid ${theme.palette.action.disabledBackground}`
            },
            "&:hover": {
              borderColor:
                theme.palette.mode === "light"
                  ? "rgba(0, 0, 0, 0.23)"
                  : "rgba(255, 255, 255, 0.23)",
              backgroundColor: alpha(
                theme.palette.text.primary,
                theme.palette.action.hoverOpacity
              )
            }
          }
        },
        {
          props: { color: "grey", variant: "text" },
          style: {
            color: theme.palette.text.primary,
            "&:hover": {
              backgroundColor: alpha(
                theme.palette.text.primary,
                theme.palette.action.hoverOpacity
              )
            }
          }
        }
      ]
    }
  }
});
// End "default" button color restoration

const router = createBrowserRouter([
  {
    path: "*",
    element: (
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <App />
        </ThemeProvider>
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
