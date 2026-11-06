import { Table, StringColumn, ReferenceColumn, BooleanColumn, IntegerColumn } from '@servicenow/sdk/core'

/**
 * Autonomous AI Case Routing Log
 * Scoped custom table generated via ServiceNow Fluent SDK
 */
export const x_demo_ai_routing_log = Table({
    name: 'x_demo_ai_routing_log',
    label: 'AI Routing Log',
    schema: {
        incident_ref: ReferenceColumn({
            label: 'Incident Reference',
            referenceTable: 'incident',
            mandatory: true,
        }),
        predicted_category: StringColumn({
            label: 'Predicted Category',
            maxLength: 40,
        }),
        confidence_score: IntegerColumn({
            label: 'Confidence Score (0-100)',
        }),
        auto_routed: BooleanColumn({
            label: 'Auto-Routed by Agent',
        }),
    },
})
