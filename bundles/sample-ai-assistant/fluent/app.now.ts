import { Record, Table } from '@servicenow/sdk/core'

/**
 * Autonomous AI Case Routing Log
 * Scoped custom table generated via ServiceNow Fluent SDK
 */
export const x_demo_ai_routing_log = Table({
    name: 'x_demo_ai_routing_log',
    label: 'AI Routing Log',
    schema: {
        incident_ref: Record({
            label: 'Incident Reference',
            reference: 'incident',
            mandatory: true,
        }),
        predicted_category: Record({
            label: 'Predicted Category',
            maxLength: 40,
        }),
        confidence_score: Record({
            label: 'Confidence Score (0-100)',
            maxLength: 10,
        }),
        auto_routed: Record({
            label: 'Auto-Routed by Agent',
        }),
    },
})
