import React from "react";
import { Route, Switch } from "react-router-dom";

import ModalContainer from 'react-modal-promise'

import { GlobalProvider } from './context/GlobalContext';

import Login from "./pages/Login/login";
import Register from "./pages/Register/register";
import RegistrationPending from "./pages/registration_pending";
import RegistrationActivation from "./pages/registration_activation";
import Dashboard from "./pages/Dashboard";

import * as path from "./constants/routes";

const App: React.FC = () => (
  <GlobalProvider>
    <ModalContainer />
    <Switch>
      <Route exact path={path.LOGIN} component={Login} />
      <Route exact path={path.REGISTER} component={Register} />
      <Route exact path={path.REGISTRATION_PENDING} component={RegistrationPending} />
      <Route exact path={path.REGISTRATION_ACTIVATION} component={RegistrationActivation} />
      <Dashboard />
    </Switch>
  </GlobalProvider>
);

export default App;