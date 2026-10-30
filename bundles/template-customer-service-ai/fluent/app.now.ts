import { Application } from '@servicenow/sdk/core';

export default Application({
  name: '{{customer_name}} AI Assistant',
  scope: 'x_{{customer_name_clean}}_ai',
});
