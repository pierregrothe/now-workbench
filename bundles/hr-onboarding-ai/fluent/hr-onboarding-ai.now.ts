import { Table, StringColumn, ReferenceColumn, BooleanColumn, IntegerColumn } from '@servicenow/sdk/core';

export const x_snc_hr_onboarding_ai_case = Table({
  name: 'x_snc_hr_onboarding_ai_case',
  label: 'Acme Corp Human Resources Case',
  schema: {
    correlation_id: StringColumn({ label: 'Correlation ID', mandatory: true, maxLength: 40 }),
    use_case_summary: StringColumn({ label: 'Use Case Summary', mandatory: true, maxLength: 255 }),
    customer_context: StringColumn({ label: 'Customer Context', mandatory: false, maxLength: 500 }),
    source_incident: ReferenceColumn({ label: 'Source Incident', referenceTable: 'incident', mandatory: true }),
    ai_confidence: IntegerColumn({ label: 'Now Assist Confidence (%)', mandatory: true }),
    automated_remediation: BooleanColumn({ label: 'Automated Remediation', mandatory: false }),
  },
});
