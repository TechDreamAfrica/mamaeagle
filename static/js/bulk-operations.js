/**
 * Bulk Operations Mixin for Alpine.js Components
 * Provides standardized bulk selection and operations functionality
 * 
 * Usage in Alpine.js components:
 * x-data="{ ...bulkOperationsMixin('invoice'), ...otherData }"
 */

function bulkOperationsMixin(entityType) {
  return {
    // Bulk operations state
    selectedItems: [],
    selectAll: false,
    showBulkDeleteModal: false,
    
    // Entity type for API calls (e.g., 'invoice', 'expense', 'customer')
    entityType: entityType,
    
    // Computed properties
    get canDeleteSelected() {
      return this.deletableCount > 0;
    },

    get deletableCount() {
      if (!this.itemData || !Array.isArray(this.itemData)) {
        return 0;
      }
      
      return this.selectedItems.filter(id => {
        const item = this.itemData.find(item => item.id === id);
        // Different deletion rules for different entity types
        switch (this.entityType) {
          case 'invoice':
            return item && item.status !== 'paid';
          case 'expense':
            return item && item.status !== 'reimbursed';
          default:
            return true; // Allow deletion for other entity types
        }
      }).length;
    },

    // Selection methods
    toggleSelectAll() {
      if (this.selectAll) {
        // Deselect all
        this.selectedItems = [];
        this.selectAll = false;
      } else {
        // Select all visible items
        if (this.itemData && Array.isArray(this.itemData)) {
          this.selectedItems = this.itemData.map(item => item.id);
          this.selectAll = true;
        }
      }
    },

    toggleItemSelection(itemId) {
      const index = this.selectedItems.indexOf(itemId);
      if (index > -1) {
        this.selectedItems.splice(index, 1);
      } else {
        this.selectedItems.push(itemId);
      }
      
      // Update select all checkbox state
      if (this.itemData && Array.isArray(this.itemData)) {
        this.selectAll = this.selectedItems.length === this.itemData.length;
      }
    },

    isItemSelected(itemId) {
      return this.selectedItems.includes(itemId);
    },

    clearSelection() {
      this.selectedItems = [];
      this.selectAll = false;
    },

    // Bulk operations
    bulkDelete() {
      if (this.deletableCount === 0) {
        let message = 'No deletable items selected.';
        if (this.entityType === 'invoice') {
          message += ' Paid invoices cannot be deleted.';
        } else if (this.entityType === 'expense') {
          message += ' Reimbursed expenses cannot be deleted.';
        }
        alert(message);
        return;
      }
      this.showBulkDeleteModal = true;
    },

    async confirmBulkDelete() {
      try {
        console.log(`Bulk deleting ${this.entityType}s:`, this.selectedItems);

        const deletableIds = this.selectedItems.filter(id => {
          const item = this.itemData.find(item => item.id === id);
          switch (this.entityType) {
            case 'invoice':
              return item && item.status !== 'paid';
            case 'expense':
              return item && item.status !== 'reimbursed';
            default:
              return true;
          }
        });

        const formData = new FormData();
        formData.append('item_ids', JSON.stringify(deletableIds));
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

        const response = await fetch(`/${this.entityType.toLowerCase()}s/bulk-delete/`, {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const result = await response.json();
          console.log('Bulk delete successful:', result);
          
          // Close modal and reset selections
          this.showBulkDeleteModal = false;
          this.clearSelection();
          
          // Show success message
          this.showSuccessMessage(`${result.deleted_count} ${this.entityType}(s) deleted successfully!`);
          
          // Reload page to update the list
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          const errorText = await response.text();
          console.error(`Error bulk deleting ${this.entityType}s:`, errorText);
          alert(`Error deleting ${this.entityType}s. Please try again.`);
          this.showBulkDeleteModal = false;
        }
      } catch (error) {
        console.error('Network error:', error);
        alert('Network error. Please check your connection and try again.');
        this.showBulkDeleteModal = false;
      }
    },

    bulkExport() {
      if (this.selectedItems.length === 0) {
        alert(`Please select ${this.entityType}s to export.`);
        return;
      }

      console.log(`Bulk exporting ${this.entityType}s:`, this.selectedItems);
      
      // Create a form to submit the selected IDs
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = `/${this.entityType.toLowerCase()}s/bulk-export/`;
      
      // Add CSRF token
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = document.querySelector('[name=csrfmiddlewaretoken]').value;
      form.appendChild(csrfInput);
      
      // Add selected item IDs
      const idsInput = document.createElement('input');
      idsInput.type = 'hidden';
      idsInput.name = 'item_ids';
      idsInput.value = JSON.stringify(this.selectedItems);
      form.appendChild(idsInput);
      
      // Submit form
      document.body.appendChild(form);
      form.submit();
      document.body.removeChild(form);
      
      // Show feedback
      this.showSuccessMessage(`Exporting ${this.selectedItems.length} ${this.entityType}(s)...`);
    },

    // Utility methods
    showSuccessMessage(message) {
      if (typeof showToast !== 'undefined') {
        showToast(message, 'success');
      } else {
        // Fallback to console log if toast function not available
        console.log('Success:', message);
      }
    },

    showErrorMessage(message) {
      if (typeof showToast !== 'undefined') {
        showToast(message, 'error');
      } else {
        alert(message);
      }
    },

    // Bulk action button classes for consistent styling
    get bulkActionClasses() {
      return {
        export: 'bg-blue-600 border border-transparent rounded-md shadow-sm py-2 px-4 inline-flex justify-center text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
        delete: 'bg-red-600 border border-transparent rounded-md shadow-sm py-2 px-4 inline-flex justify-center text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500',
        clear: 'bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600'
      };
    }
  };
}

/**
 * Bulk Delete Modal Component
 * Generates HTML for a standardized bulk delete confirmation modal
 */
function generateBulkDeleteModal(entityType) {
  return `
    <div
      x-show="showBulkDeleteModal"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50"
      x-cloak
      style="display: none"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">
              <i class="fas fa-exclamation-triangle text-red-600 mr-2"></i>Bulk Delete ${entityType.charAt(0).toUpperCase() + entityType.slice(1)}s
            </h3>
            <button
              @click="showBulkDeleteModal = false"
              class="text-gray-400 hover:text-gray-600"
            >
              <i class="fas fa-times"></i>
            </button>
          </div>
        </div>

        <div class="px-6 py-4">
          <div class="text-sm text-gray-500 mb-4">
            Are you sure you want to delete the selected ${entityType}s? This action cannot be undone.
          </div>
          
          <div class="bg-gray-50 rounded-lg p-4 mb-4">
            <div class="text-sm">
              <div class="font-medium text-gray-900" x-text="\`\${deletableCount} ${entityType}(s) will be deleted\`"></div>
              <div class="text-gray-600 mt-1" x-show="selectedItems.length !== deletableCount">
                <i class="fas fa-info-circle mr-1"></i>
                <span x-text="\`\${selectedItems.length - deletableCount} ${entityType}(s) will be skipped\`"></span>
              </div>
            </div>
          </div>

          <div class="flex justify-end space-x-3">
            <button
              @click="showBulkDeleteModal = false"
              type="button"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-dreambiz-500"
            >
              Cancel
            </button>
            <button
              @click="confirmBulkDelete()"
              type="button"
              class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <i class="fas fa-trash mr-2"></i>Delete Selected
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

/**
 * Bulk Actions Header Component
 * Generates HTML for bulk action buttons
 */
function generateBulkActionsHeader(entityType) {
  return `
    <div x-show="selectedItems.length > 0" class="flex space-x-2">
      <button
        @click="bulkExport()"
        type="button"
        x-bind:class="bulkActionClasses.export"
      >
        <i class="fas fa-download mr-2"></i>Export Selected (<span x-text="selectedItems.length"></span>)
      </button>
      <button
        @click="bulkDelete()"
        type="button"
        x-bind:class="bulkActionClasses.delete"
        x-show="canDeleteSelected"
      >
        <i class="fas fa-trash mr-2"></i>Delete Selected (<span x-text="deletableCount"></span>)
      </button>
    </div>
  `;
}

// Export for use in templates
if (typeof window !== 'undefined') {
  window.bulkOperationsMixin = bulkOperationsMixin;
  window.generateBulkDeleteModal = generateBulkDeleteModal;
  window.generateBulkActionsHeader = generateBulkActionsHeader;
}
