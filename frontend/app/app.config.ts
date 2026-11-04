export default defineAppConfig({
  ui: {
    colors: {
      primary: 'indigo',
      neutral: 'zinc'
    },
    // Rows that open something (the deliveries table) show it on hover.
    table: {
      slots: {
        tbody: '[&>tr]:data-[selectable=true]:cursor-pointer'
      }
    }
  }
})
