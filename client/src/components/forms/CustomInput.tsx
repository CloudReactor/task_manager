import React, { Fragment } from "react";
import Form from 'react-bootstrap/Form';
import styles from './CustomInput.module.scss';

import {
  FormGroup,
  FormLabel,
  FormText,
} from 'react-bootstrap';

interface Props {
  field: {
    name: string;
    value: string;
  };
  form?: {
    touched: any;
    errors: any;
  };
  controlId?: string;
  label?: string;
  subText?: string;
  type?: any;
  addOptionsCase?: boolean;
  options?: [];
  min?: number;
  omitLabel?: boolean,
  [propName: string]: any;
}

function capitalize (s: string) {
  if (typeof s !== 'string') return ''
  return s.charAt(0).toUpperCase() + s.slice(1)
}

const CustomInput = ({
  field,
  form,
  controlId,
  subText,
  label,
  type,
  addOptionsCase,
  options,
  min,
  omitLabel,
  ...props
}: Props) => {

  const resolvedForm = form ?? {
    touched: {},
    errors: {}
  };

  const {
    touched,
    errors
  } = resolvedForm;

  const optionsList = options?.map((option, i) => {
    const updatedOption = (option === 'none') ? '' : option;
    return (
      <option value={updatedOption} key={`option-${i}`}>
        {addOptionsCase ? capitalize(option) : option}
      </option>
    );
  });

  return (
    <FormGroup controlId={controlId}>
      {
        (type === 'select') ? (
          <Fragment>
            { !omitLabel && <FormLabel>{label}</FormLabel> }
            <Form.Control
              as="select"
              {...field}
              {...props}
              isInvalid={touched[field.name] && errors[field.name]}
            >
              {optionsList}
            </Form.Control>
          </Fragment>
        ) : (type === 'checkbox') ? (
          <Form.Check
            type={type}
            label={label}
            {...field}
            {...props}
            isInvalid={touched[field.name] && errors[field.name]}
          />
        ) : (type === 'radio') ? (
          <Form.Check
            type={type}
            label={label}
            {...field}
            {...props}
            isInvalid={touched[field.name] && errors[field.name]}
          />
        ) : (
          <Fragment>
            { !omitLabel && <FormLabel>{label}</FormLabel> }
            <Form.Control
              type={type}
              value={field.value || ''}
              name={field.name}
              min={min}
              {...props}
              isInvalid={touched[field.name] && errors[field.name]}
            />
          </Fragment>
        )
      }

      {touched[field.name] && errors[field.name] && (
        <div className="error text-danger">{errors[field.name]}</div>
      )}
      {subText && <FormText className={styles.subText}>{subText}</FormText>}
    </FormGroup>
  );
}

export default CustomInput;
