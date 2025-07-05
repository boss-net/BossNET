"use client"

import React from "react"
import { useForm, type FieldValues } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { LoadingSpinner } from "@/components/ui/loading-spinner"
import { AlertCircle, CheckCircle } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

// Common validation schemas
export const commonValidations = {
  email: z.string().email("Please enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      "Password must contain at least one uppercase letter, one lowercase letter, and one number",
    ),
  phone: z.string().regex(/^(\+88)?01[3-9]\d{8}$/, "Please enter a valid Bangladeshi phone number"),
  nid: z.string().regex(/^\d{10}$|^\d{13}$|^\d{17}$/, "Please enter a valid National ID number"),
  name: z.string().min(2, "Name must be at least 2 characters").max(50, "Name must not exceed 50 characters"),
  required: z.string().min(1, "This field is required"),
  positiveNumber: z.number().positive("Must be a positive number"),
  nonNegativeNumber: z.number().min(0, "Must be zero or positive"),
  url: z.string().url("Please enter a valid URL"),
  date: z.date({
    required_error: "Please select a date",
    invalid_type_error: "Please enter a valid date",
  }),
}

// Student enrollment form schema
export const studentEnrollmentSchema = z.object({
  studentId: z.string().min(1, "Student ID is required"),
  firstName: commonValidations.name,
  lastName: commonValidations.name,
  email: commonValidations.email.optional(),
  phone: commonValidations.phone.optional(),
  dateOfBirth: commonValidations.date,
  gender: z.enum(["male", "female", "other"], {
    required_error: "Please select a gender",
  }),
  address: z.string().min(10, "Address must be at least 10 characters"),
  division: z.string().min(1, "Please select a division"),
  district: z.string().min(1, "Please select a district"),
  upazila: z.string().min(1, "Please select an upazila"),
  schoolId: z.string().min(1, "Please select a school"),
  class: z.string().min(1, "Please select a class"),
  section: z.string().optional(),
  academicYear: z.string().min(1, "Please select an academic year"),
  guardianName: commonValidations.name,
  guardianPhone: commonValidations.phone,
  guardianRelation: z.string().min(1, "Please specify guardian relation"),
  previousSchool: z.string().optional(),
  transferCertificate: z.boolean().default(false),
  medicalConditions: z.string().optional(),
  specialNeeds: z.string().optional(),
  consent: z.boolean().refine((val) => val === true, {
    message: "You must provide consent to proceed",
  }),
})

export type StudentEnrollmentFormData = z.infer<typeof studentEnrollmentSchema>

// School registration form schema
export const schoolRegistrationSchema = z.object({
  schoolName: z.string().min(3, "School name must be at least 3 characters"),
  schoolCode: z.string().min(1, "School code is required"),
  schoolType: z.enum(["government", "private", "madrasa", "technical"], {
    required_error: "Please select a school type",
  }),
  level: z.enum(["primary", "secondary", "higher_secondary"], {
    required_error: "Please select a school level",
  }),
  address: z.string().min(10, "Address must be at least 10 characters"),
  division: z.string().min(1, "Please select a division"),
  district: z.string().min(1, "Please select a district"),
  upazila: z.string().min(1, "Please select an upazila"),
  postalCode: z.string().regex(/^\d{4}$/, "Please enter a valid postal code"),
  phone: commonValidations.phone,
  email: commonValidations.email,
  website: commonValidations.url.optional(),
  establishedYear: z
    .number()
    .min(1800, "Established year must be after 1800")
    .max(new Date().getFullYear(), "Established year cannot be in the future"),
  principalName: commonValidations.name,
  principalPhone: commonValidations.phone,
  principalEmail: commonValidations.email,
  totalStudents: commonValidations.nonNegativeNumber,
  totalTeachers: commonValidations.positiveNumber,
  facilities: z.array(z.string()).min(1, "Please select at least one facility"),
  hasLibrary: z.boolean().default(false),
  hasLaboratory: z.boolean().default(false),
  hasPlayground: z.boolean().default(false),
  hasComputer: z.boolean().default(false),
  hasInternet: z.boolean().default(false),
  registrationCertificate: z.boolean().refine((val) => val === true, {
    message: "Registration certificate is required",
  }),
})

export type SchoolRegistrationFormData = z.infer<typeof schoolRegistrationSchema>

interface ValidatedFormProps<T extends FieldValues> {
  schema: z.ZodSchema<T>
  defaultValues?: Partial<T>
  onSubmit: (data: T) => Promise<void> | void
  onError?: (errors: any) => void
  children: (props: {
    form: ReturnType<typeof useForm<T>>
    isSubmitting: boolean
    errors: any
  }) => React.ReactNode
  className?: string
  submitButtonText?: string
  showSubmitButton?: boolean
  isLoading?: boolean
  successMessage?: string
  errorMessage?: string
}

export function ValidatedForm<T extends FieldValues>({
  schema,
  defaultValues,
  onSubmit,
  onError,
  children,
  className,
  submitButtonText = "Submit",
  showSubmitButton = true,
  isLoading = false,
  successMessage,
  errorMessage,
}: ValidatedFormProps<T>) {
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [submitError, setSubmitError] = React.useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = React.useState<string | null>(null)

  const form = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues as any,
    mode: "onChange",
  })

  const handleSubmit = async (data: T) => {
    try {
      setIsSubmitting(true)
      setSubmitError(null)
      setSubmitSuccess(null)

      await onSubmit(data)

      if (successMessage) {
        setSubmitSuccess(successMessage)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "An error occurred while submitting the form"
      setSubmitError(errorMessage || message)
      onError?.(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className={cn("space-y-6", className)} noValidate>
        {submitSuccess && (
          <Alert className="border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">{submitSuccess}</AlertDescription>
          </Alert>
        )}

        {submitError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        )}

        {children({
          form,
          isSubmitting: isSubmitting || isLoading,
          errors: form.formState.errors,
        })}

        {showSubmitButton && (
          <Button type="submit" disabled={isSubmitting || isLoading || !form.formState.isValid} className="w-full">
            {(isSubmitting || isLoading) && <LoadingSpinner size="sm" className="mr-2" />}
            {submitButtonText}
          </Button>
        )}
      </form>
    </Form>
  )
}

// Example usage components
export const StudentEnrollmentForm: React.FC<{
  onSubmit: (data: StudentEnrollmentFormData) => Promise<void>
  defaultValues?: Partial<StudentEnrollmentFormData>
  isLoading?: boolean
}> = ({ onSubmit, defaultValues, isLoading }) => {
  return (
    <ValidatedForm
      schema={studentEnrollmentSchema}
      defaultValues={defaultValues}
      onSubmit={onSubmit}
      isLoading={isLoading}
      submitButtonText="Enroll Student"
      successMessage="Student enrolled successfully!"
      className="max-w-2xl mx-auto"
    >
      {({ form, isSubmitting }) => (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="firstName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>First Name</FormLabel>
                  <FormControl>
                    <input
                      {...field}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="Enter first name"
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="lastName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Last Name</FormLabel>
                  <FormControl>
                    <input
                      {...field}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="Enter last name"
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email (Optional)</FormLabel>
                <FormControl>
                  <input
                    {...field}
                    type="email"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="Enter email address"
                    disabled={isSubmitting}
                  />
                </FormControl>
                <FormDescription>Email will be used for important notifications</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="consent"
            render={({ field }) => (
              <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                <FormControl>
                  <input
                    type="checkbox"
                    checked={field.value}
                    onChange={field.onChange}
                    disabled={isSubmitting}
                    className="h-4 w-4 rounded border border-input"
                  />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel>I consent to the collection and processing of this data</FormLabel>
                  <FormDescription>By checking this box, you agree to our data processing policies</FormDescription>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />
        </>
      )}
    </ValidatedForm>
  )
}

export default ValidatedForm
