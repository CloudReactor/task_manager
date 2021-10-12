import { Group, User } from  '../types/website_types';

import React, { createContext, useState } from 'react';

export type GlobalContextType = {
  currentUser?: User,
  setCurrentUser: (user: User) => void,
  currentGroup?: Group,
  setCurrentGroup: (group: Group) => void
}

const initialState: GlobalContextType = {
  setCurrentUser: (user: User) => {},
  setCurrentGroup: (group: Group) => {}
};

export const GlobalContext = createContext<GlobalContextType>(initialState);

const STORAGE_KEY_CURRENT_GROUP_ID = 'currentGroupId';

type Props = {
  children: React.ReactNode
};

export const GlobalProvider = ({ children }: Props) => {
  const [currentUser, setCurrentUser] = useState(initialState.currentUser);
  const [currentGroup, setCurrentGroup] = useState(initialState.currentGroup);

  const setCurrentGroupWithGroupIdSaving = (group: Group) => {
    setCurrentGroup(group);
    try {
      window.sessionStorage.setItem(STORAGE_KEY_CURRENT_GROUP_ID, '' + group.id);
      window.localStorage.setItem(STORAGE_KEY_CURRENT_GROUP_ID, '' + group.id);
    } catch (ex) {
      // No session or local storage available
    }
  };

  return (
    <GlobalContext.Provider value={{
      currentUser, setCurrentUser,
      currentGroup,
      setCurrentGroup: setCurrentGroupWithGroupIdSaving
    }}>
      {children}
    </GlobalContext.Provider>
  );
};

export function accessLevelForCurrentGroup(context: GlobalContextType): number|null {
  const {
    currentUser,
    currentGroup
  } = context;

  if (!currentUser || !currentGroup) {
    return null;
  }

  return currentUser.group_access_levels[currentGroup.id] ?? null;
}

export function getSavedCurrentGroupId(): number|null {
  let groupIdString: string|null;

  try {
    groupIdString = window.sessionStorage.getItem(STORAGE_KEY_CURRENT_GROUP_ID);
    if (groupIdString) {
      return parseInt(groupIdString);
    }
  } catch (ex) {
    ;
  }

  try {
    groupIdString = window.localStorage.getItem(STORAGE_KEY_CURRENT_GROUP_ID);
    if (groupIdString) {
      return parseInt(groupIdString);
    }
  } catch (ex) {
    ;
  }

  return null;
}