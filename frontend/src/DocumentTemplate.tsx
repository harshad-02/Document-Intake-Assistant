import React from 'react';
import type { StateSnapshot } from './api';
import './template.css';

export interface DocumentTemplateProps {
  state: StateSnapshot | null;
}

export function DocumentTemplate({ state }: DocumentTemplateProps) {
  // Helper to extract value safely
  const getVal = (field: keyof StateSnapshot, fallback = '') => {
    if (!state) return fallback;
    const f = state[field];
    if (f && f.status === 'confirmed' && f.value != null) {
      return f.value;
    }
    return fallback;
  };

  const fullName = getVal('full_name') as string;
  const homeAddress = getVal('home_address') as string;
  
  const coversWorldwide = getVal('covers_worldwide_assets') as boolean | string;
  const isWorldwide = coversWorldwide === true || coversWorldwide === 'worldwide';
  const isSpecific = coversWorldwide !== '' && !isWorldwide && coversWorldwide !== null && coversWorldwide !== undefined;
  const specificAssetsText = (isSpecific && typeof coversWorldwide === 'string' && coversWorldwide !== 'specific') ? coversWorldwide : '';

  const hasChildren = getVal('has_children') as boolean | string;
  const isYesChildren = hasChildren === true;
  const isNoChildren = hasChildren === false;

  let childrenList = getVal('children', []) as string[];
  if (!Array.isArray(childrenList)) childrenList = [];
  
  const executorName = getVal('executor_name') as string;
  const executorRel = getVal('executor_relationship') as string;

  let specificGifts = getVal('specific_gifts', []) as string[];
  if (!Array.isArray(specificGifts)) specificGifts = [];

  let additionalWishes = getVal('additional_wishes', []) as string[];
  if (!Array.isArray(additionalWishes)) additionalWishes = [];

  return (
    <div className="pdf-template-wrapper">
      <div className="pdf-header">
        <h1>My Personal Wishes</h1>
        <div className="pdf-divider">
          <span className="pdf-leaf-icon">🌿</span>
        </div>
        <h2>A PERSONAL WISHES DOCUMENT</h2>
      </div>

      <div className="pdf-section">
        <div className="pdf-section-header">
          1. PERSONAL INFORMATION
        </div>
        <div className="pdf-section-body">
          <div className="pdf-row">
            <span className="pdf-label">Full Name:</span>
            <span className="pdf-value">{fullName}</span>
          </div>
          <div className="pdf-row">
            <span className="pdf-label">Home Address:</span>
            <span className="pdf-value">{homeAddress}</span>
          </div>
        </div>
      </div>

      <div className="pdf-section">
        <div className="pdf-section-header">
          2. DOCUMENT COVERAGE
        </div>
        <div className="pdf-section-body">
          <div className="pdf-text">This document covers:</div>
          <div className="pdf-checkbox-row">
            <div className="pdf-checkbox">{isWorldwide ? '✔' : ''}</div>
            <span>Worldwide assets (properties, bank accounts, investments, etc.)</span>
          </div>
          <div className="pdf-checkbox-row">
            <div className="pdf-checkbox">{isSpecific ? '✔' : ''}</div>
            <span>Specific assets only (please specify): </span>
            <span className="pdf-value inline-value">{specificAssetsText}</span>
          </div>
        </div>
      </div>

      <div className="pdf-section">
        <div className="pdf-section-header">
          3. FAMILY INFORMATION
        </div>
        <div className="pdf-section-body">
          <div className="pdf-checkbox-group">
            <span className="pdf-label-inline">Do you have children?</span>
            <div className="pdf-checkbox">{isYesChildren ? '✔' : ''}</div> <span>Yes</span>
            <div className="pdf-checkbox" style={{ marginLeft: '1rem' }}>{isNoChildren ? '✔' : ''}</div> <span>No</span>
          </div>
          <div className="pdf-text" style={{ marginTop: '8px', marginBottom: '8px' }}>
            If yes, please provide their names:
          </div>
          <table className="pdf-table">
            <thead>
              <tr>
                <th style={{ width: '10%' }}>No.</th>
                <th style={{ width: '90%' }}>Name</th>
              </tr>
            </thead>
            <tbody>
              {childrenList.length > 0 ? (
                childrenList.map((child, i) => (
                  <tr key={i}>
                    <td className="text-center">{i + 1}</td>
                    <td>{child}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="text-center">1</td>
                  <td></td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pdf-section">
        <div className="pdf-section-header">
          4. EXECUTOR INFORMATION
        </div>
        <div className="pdf-section-body">
          <div className="pdf-row">
            <span className="pdf-label" style={{ width: '160px' }}>Name of Executor:</span>
            <span className="pdf-value">{executorName}</span>
          </div>
          <div className="pdf-row">
            <span className="pdf-label" style={{ width: '160px' }}>Relationship to You:</span>
            <span className="pdf-value">{executorRel}</span>
          </div>
        </div>
      </div>

      <div className="pdf-section">
        <div className="pdf-section-header">
          5. SPECIFIC GIFTS
        </div>
        <div className="pdf-section-body">
          <div className="pdf-text" style={{ marginBottom: '8px' }}>
            If you would like to leave any specific gifts to individuals or organizations, please list them below:
          </div>
          <table className="pdf-table">
            <thead>
              <tr>
                <th style={{ width: '10%' }}>No.</th>
                <th style={{ width: '90%' }}>Gift Description</th>
              </tr>
            </thead>
            <tbody>
              {specificGifts.length > 0 ? (
                specificGifts.map((gift, i) => (
                  <tr key={i}>
                    <td className="text-center">{i + 1}</td>
                    <td>{gift}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="text-center">1</td>
                  <td></td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pdf-section">
        <div className="pdf-section-header">
          6. ADDITIONAL WISHES
        </div>
        <div className="pdf-section-body">
          <div className="pdf-text" style={{ marginBottom: '8px' }}>
            Please share any additional wishes, instructions, or messages you would like to include:
          </div>
          <div className="pdf-wishes-box">
            {additionalWishes.length > 0 ? (
              <div className="pdf-wishes-text">{additionalWishes.join(', ')}</div>
            ) : (
              <>
                <div className="pdf-line"></div>
                <div className="pdf-line"></div>
                <div className="pdf-line"></div>
              </>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
