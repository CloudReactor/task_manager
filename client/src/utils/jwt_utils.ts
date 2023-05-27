const TOKEN_CONTAINER_PROPERTY_NAME = 'tokenContainer';

export function readTokenContainer() {
  try {
    return JSON.parse(window.localStorage.getItem(TOKEN_CONTAINER_PROPERTY_NAME) || '{}');
  } catch (e) {
    return {};
  }
}

export const saveToken = (data: any): string => {
  let oldRefresh = null;

  try {
    const oldContainer = readTokenContainer();
    oldRefresh = oldContainer.refresh
  } catch (e) {
    ;
  }

  const tokenContainer = JSON.stringify({
    access: data.access,
    refresh: data.refresh || oldRefresh,
    time: +new Date()
  });
  window.localStorage.setItem(TOKEN_CONTAINER_PROPERTY_NAME, tokenContainer);
  return tokenContainer;
};

export function removeTokenContainer() {
  window.localStorage.removeItem(TOKEN_CONTAINER_PROPERTY_NAME);
}
