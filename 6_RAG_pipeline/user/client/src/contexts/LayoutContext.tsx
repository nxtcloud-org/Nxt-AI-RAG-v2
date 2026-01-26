import React, { createContext, useContext } from 'react';

interface LayoutContextType {
}

const LayoutContext = createContext<LayoutContextType>({});

export const LayoutProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <LayoutContext.Provider value={{}}>
      {children}
    </LayoutContext.Provider>
  );
};

export const useLayout = () => useContext(LayoutContext);
