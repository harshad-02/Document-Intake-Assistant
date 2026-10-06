import React, { useState, useEffect } from 'react';
import personImg from './assets/person.png';
import fieldsImg from './assets/fields.png';
import earthImg from './assets/earth.png';
import startImg from './assets/start.png';
import editImg from './assets/edit.png';
import saveImg from './assets/save.png';

const FieldInput = ({ label, value, onChange, placeholder, isTextarea = false, stacked = false, hint = '' }: any) => {
  const InputComponent = isTextarea ? 'textarea' : 'input';
  return (
    <div className={`field-group ${stacked ? 'vertical half' : ''}`}>
      <label className={`field-label-new ${stacked ? 'stacked' : ''}`}>
        {label}
      </label>
      <div style={{ flex: 1, width: '100%' }}>
        <InputComponent
          className='field-input-new'
          value={value}
          onChange={(e: any) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        {hint && <div className='input-hint'>{hint}</div>}
      </div>
    </div>
  );
};

const FieldRadio = ({ label, value, onChange, options, name }: any) => {
  return (
    <div className='field-group'>
      <label className='field-label-new'>
        {label}
      </label>
      <div className='radio-group-new'>
        {options.map((opt: any, index: number) => (
          <label key={opt.label} className='radio-label-new'>
            <input
              type='radio'
              name={name || label}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
            />
            {opt.label}
          </label>
        ))}
      </div>
    </div>
  );
};

const EditCard = ({ title, icon, children }: any) => (
  <div className='edit-card'>
    <div className='edit-card-icon'>
      <img src={icon} alt={title} />
    </div>
    <div className='edit-card-content'>
      <div className='edit-card-header'>
        <h3 className='edit-card-title'>{title}</h3>
      </div>
      <div className='edit-card-fields'>{children}</div>
    </div>
  </div>
);

export const EditPanel = ({ state, onSave }: any) => {
  const [localState, setLocalState] = useState<any>(null);

  useEffect(() => {
    if (state) {
      setLocalState({
        full_name: state.full_name?.value || '',
        home_address: state.home_address?.value || '',
        covers_worldwide_assets: typeof state.covers_worldwide_assets?.value === 'object' ? state.covers_worldwide_assets?.value?.worldwide : state.covers_worldwide_assets?.value,
        has_children: state.has_children?.value,
        children: state.children?.value || '',
        executor_name: state.executor_name?.value || '',
        executor_relationship: state.executor_relationship?.value || '',
        specific_gifts: state.specific_gifts?.value || '',
        additional_wishes: state.additional_wishes?.value || ''
      });
    }
  }, [state]);

  if (!localState) return <div style={{ padding: '2rem' }}>Loading state...</div>;

  const handleChange = (field: string, val: any) => {
    setLocalState((prev: any) => ({ ...prev, [field]: val }));
  };

  const handleSaveClick = () => {
    onSave(localState);
  };

  const noChildren = localState.has_children === false;

  return (
    <div className='edit-panel-container'>
      <div className="panel-header" style={{ marginBottom: '0.5rem', backgroundColor: 'white', padding: '1rem 1.5rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', boxShadow: 'var(--shadow-sm)' }}>
        <div className="panel-title">
          <img src={fieldsImg} alt="Fields Icon" className="panel-title-icon-img" /> Fields
        </div>
        <div className="doc-actions">
          <button className="btn-doc-action" onClick={handleSaveClick}>
            <img src={saveImg} alt="Save Icon" className="btn-action-icon" style={{ filter: 'brightness(0)' }} /> Save Changes
          </button>
        </div>
      </div>

      <EditCard title='Personal Information' icon={personImg}>
        <FieldInput
          label='Full Name'
          value={localState.full_name}
          onChange={(val: any) => handleChange('full_name', val)}
        />
        <FieldInput
          label='Home Address'
          value={localState.home_address}
          onChange={(val: any) => handleChange('home_address', val)}
          isTextarea
        />
      </EditCard>

      <EditCard title='Assets Coverage' icon={earthImg}>
        <FieldRadio
          name='assets_coverage'
          label='Does this document cover your worldwide assets?'
          value={localState.covers_worldwide_assets}
          onChange={(val: any) => handleChange('covers_worldwide_assets', val)}
          options={[
            { label: 'Yes, worldwide assets', value: true },
            { label: 'No, only assets in a specific country', value: false },
          ]}
        />
      </EditCard>

      <EditCard title='Family' icon={personImg}>
        <div className='field-row-flex'>
          <div style={{ flex: 1 }}>
            <FieldRadio
              name='has_children'
              label='Do you have children?'
              value={localState.has_children}
              onChange={(val: any) => handleChange('has_children', val)}
              options={[
                { label: 'Yes', value: true },
                { label: 'No', value: false },
              ]}
            />
          </div>
          {!noChildren && (
            <FieldInput
              label='Children Names'
              value={localState.children}
              onChange={(val: any) => handleChange('children', val)}
              isTextarea
              stacked
              hint='Enter the names of your children, separated by commas.'
            />
          )}
        </div>
      </EditCard>

      <EditCard title='Executor' icon={personImg}>
        <div className='field-row-flex'>
          <FieldInput
            label='Executor Name'
            value={localState.executor_name}
            onChange={(val: any) => handleChange('executor_name', val)}
            stacked
          />
          <FieldInput
            label='Relationship to you'
            value={localState.executor_relationship}
            onChange={(val: any) => handleChange('executor_relationship', val)}
            stacked
          />
        </div>
      </EditCard>

      <EditCard title='Specific Gifts' icon={startImg}>
        <FieldInput
          label='Any specific gifts you would like to include?'
          value={localState.specific_gifts}
          onChange={(val: any) => handleChange('specific_gifts', val)}
          isTextarea
        />
      </EditCard>

      <EditCard title='Additional Wishes' icon={editImg}>
        <FieldInput
          label='Any additional wishes or instructions?'
          value={localState.additional_wishes}
          onChange={(val: any) => handleChange('additional_wishes', val)}
          isTextarea
        />
      </EditCard>
    </div>
  );
};
