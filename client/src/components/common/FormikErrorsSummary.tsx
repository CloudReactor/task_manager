import React from 'react';

interface Props {
  errors: any;
  touched: any;
  values: any;
}

const FormikErrorsSummary = ({ errors }: Props) => {
  const errorKeys = Object.keys(errors);

  if (errorKeys.length === 0) {
    return null;
  }

  return (
    <ul>{
      Object.entries(errors).flatMap(([p, err]) => {
        if (!err) {
          return [];
        }
        const errArray = Array.isArray(err) ? err : [err];
        return errArray.map(s => <li key={p}>{
          (typeof(s) === 'object') ? JSON.stringify(s) :
            s.toString()
        }</li>);
      })
    }
    </ul>
  );
}

export default FormikErrorsSummary;