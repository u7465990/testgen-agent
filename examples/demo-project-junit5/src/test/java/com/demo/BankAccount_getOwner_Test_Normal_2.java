package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

public class BankAccount_getOwner_Test_Normal_2 {


    @Test
    public void testGetOwnerReturnsConfiguredOwner() {
        // Arrange: typical valid inputs
        String expectedOwner = "Alice Johnson";
        double initialBalance = 1000.0;
        BankAccount account = new BankAccount(expectedOwner, initialBalance);

        // Act
        String actualOwner = account.getOwner();

        // Assert
        assertNotNull(actualOwner);
        assertEquals(expectedOwner, actualOwner);
    }

}
