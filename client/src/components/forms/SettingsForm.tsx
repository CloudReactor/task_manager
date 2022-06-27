import React from 'react';
import { Field } from 'formik';
import CustomInput from './CustomInput';
import styles from './SettingsForm.module.scss';

interface Props {
  items: any;
  onChange?: any;
  handleBlur?: any;
}

export const SettingsForm = (props: Props) => {

  const { items } = props || {};

  return items?.map((item: any, i: any) => {
    const {
      title,
      controls
    } = item || {};

    return (
      <div
        className={styles.formSection}
        key={`form-container-${i}`}
      >
        {
          title &&
            <div
              key={`form-section-${i}`}
              className={styles.sectionTitle}
            >
              {title}
            </div>
        }
        <div>
          {controls?.map((control: any, j: any) => {
            return (
              <Field
                key={`control-${title}-element-${j}`}
                id={control.name}
                name={control.name}
                type={control.type}
                label={control.label}
                placeholder={control.placeholder}
                component={CustomInput}
                addOptionsCase={control.addOptionsCase}
                options={control.options}
                subText={control.subText}
                onChange={props.onChange}
                onBlur={props.handleBlur}
                min={control.min}
              />
            );
          })}
        </div>
      </div>
    );
  })
}

export default SettingsForm;
