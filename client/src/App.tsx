import React from "react";
import { Route, Routes } from "react-router-dom";

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
    <Routes>
      <Route path={path.LOGIN} element={<Login/>} />
      <Route path={path.REGISTER} element={ <Register/> } />
      <Route path={path.REGISTRATION_PENDING} element={ <RegistrationPending/> } />
      <Route path={path.REGISTRATION_ACTIVATION} element={ <RegistrationActivation/> } />
      <Route path="/*" element={<Dashboard />} />
    </Routes>
  </GlobalProvider>
);

export default App;