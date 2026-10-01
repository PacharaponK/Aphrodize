"use client";

import React, { useState, useRef, useEffect, useCallback, useId } from "react";
import { ChevronDown, Check } from "lucide-react";

export interface SelectOption {
  value: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
}

export interface SelectProps {
  id?: string;
  name?: string;
  value?: string;
  defaultValue?: string;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  ariaLabel?: string;
  onChange?: (value: string) => void;
}

export function Select({
  id,
  name,
  value: controlledValue,
  defaultValue = "",
  options,
  placeholder = "เลือก...",
  disabled = false,
  required = false,
  className = "",
  ariaLabel,
  onChange,
}: SelectProps) {
  const generatedId = useId();
  const selectId = id || generatedId;
  const isControlled = controlledValue !== undefined;
  const [internalValue, setInternalValue] = useState<string>(
    isControlled ? (controlledValue ?? "") : defaultValue
  );
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);

  const currentValue = isControlled ? (controlledValue ?? "") : internalValue;
  const selectedOption = options.find((opt) => opt.value === currentValue);
  const isPlaceholder = !selectedOption || currentValue === "";

  const handleSelect = useCallback(
    (val: string) => {
      if (!isControlled) {
        setInternalValue(val);
      }
      onChange?.(val);
      setIsOpen(false);
      triggerRef.current?.focus();
    },
    [isControlled, onChange]
  );

  // Close when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent | TouchEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [isOpen]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setFocusedIndex(0);
      } else {
        setFocusedIndex((prev) => (prev + 1 < options.length ? prev + 1 : 0));
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setFocusedIndex(options.length - 1);
      } else {
        setFocusedIndex((prev) => (prev - 1 >= 0 ? prev - 1 : options.length - 1));
      }
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        const idx = options.findIndex((opt) => opt.value === currentValue);
        setFocusedIndex(idx >= 0 ? idx : 0);
      } else if (focusedIndex >= 0 && options[focusedIndex] && !options[focusedIndex].disabled) {
        handleSelect(options[focusedIndex].value);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
    } else if (e.key === "Tab") {
      setIsOpen(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`aphrodize-select-container ${disabled ? "is-disabled" : ""} ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Hidden input for standard form submission */}
      {name && (
        <input
          type="hidden"
          name={name}
          value={currentValue}
          required={required}
        />
      )}

      {/* Visually hidden select for accessible required validation if form checks validity */}
      {name && required && (
        <select
          tabIndex={-1}
          aria-hidden="true"
          required={required}
          value={currentValue}
          onChange={() => {}}
          className="aphrodize-select-hidden-native"
        >
          <option value="" disabled />
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {typeof opt.label === "string" ? opt.label : opt.value}
            </option>
          ))}
        </select>
      )}

      <button
        ref={triggerRef}
        id={selectId}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel}
        className={`aphrodize-select-trigger ${isOpen ? "is-open" : ""}`}
        onClick={() => {
          if (!disabled) {
            setIsOpen((prev) => !prev);
            const idx = options.findIndex((opt) => opt.value === currentValue);
            setFocusedIndex(idx >= 0 ? idx : 0);
          }
        }}
      >
        <span className="aphrodize-select-content">
          {selectedOption?.icon && (
            <span className="aphrodize-select-icon" aria-hidden="true">
              {selectedOption.icon}
            </span>
          )}
          <span className={`aphrodize-select-label ${isPlaceholder ? "is-placeholder" : ""}`}>
            {selectedOption ? selectedOption.label : placeholder}
          </span>
        </span>
        <span className="aphrodize-select-chevron" aria-hidden="true">
          <ChevronDown size={17} className={isOpen ? "is-rotated" : ""} />
        </span>
      </button>

      {isOpen && (
        <div
          ref={listboxRef}
          role="listbox"
          tabIndex={-1}
          aria-labelledby={selectId}
          className="aphrodize-select-menu"
        >
          {options.map((option, index) => {
            const isSelected = option.value === currentValue;
            const isFocused = index === focusedIndex;
            const isOptionDisabled = option.disabled;

            return (
              <div
                key={option.value}
                role="option"
                aria-selected={isSelected}
                aria-disabled={isOptionDisabled}
                className={`aphrodize-select-item ${isSelected ? "is-selected" : ""} ${
                  isFocused ? "is-focused" : ""
                } ${isOptionDisabled ? "is-disabled" : ""}`}
                onClick={() => {
                  if (!isOptionDisabled) {
                    handleSelect(option.value);
                  }
                }}
                onMouseEnter={() => {
                  if (!isOptionDisabled) {
                    setFocusedIndex(index);
                  }
                }}
              >
                <div className="aphrodize-select-item-content">
                  {option.icon && (
                    <span className="aphrodize-select-item-icon" aria-hidden="true">
                      {option.icon}
                    </span>
                  )}
                  <div className="aphrodize-select-item-texts">
                    <span className="aphrodize-select-item-label">{option.label}</span>
                    {option.description && (
                      <span className="aphrodize-select-item-desc">{option.description}</span>
                    )}
                  </div>
                </div>
                {isSelected && (
                  <span className="aphrodize-select-item-check" aria-hidden="true">
                    <Check size={16} strokeWidth={2.5} />
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
